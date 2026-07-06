"""
API tests: authentication, truthful status rules, ingest validation,
manual-run gating, and demo-route registration.
"""
import importlib
import os

from tests.conftest import AUTH

INGEST = {"secret": "test-ingest"}


# ── Auth ──────────────────────────────────────────────────────────────────

def test_health_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_private_routes_require_auth(client):
    private_gets = [
        "/pipeline/", "/pipeline/summary", "/briefings/history",
        "/analytics/summary", "/analytics/metrics", "/activity/recent",
        "/runs/latest", "/interview/history",
    ]
    for path in private_gets:
        r = client.get(path)
        assert r.status_code == 401, f"{path} should require auth, got {r.status_code}"


def test_wrong_token_is_rejected(client):
    r = client.get("/pipeline/", headers={"Authorization": "Bearer wrong-token"})
    assert r.status_code == 403


def test_valid_token_grants_access(client):
    r = client.get("/pipeline/", headers=AUTH)
    assert r.status_code == 200


def test_login_issues_working_session_token(client):
    r = client.post("/auth/login", json={"password": "test-pass"})
    assert r.status_code == 200
    session_token = r.json()["token"]
    r2 = client.get("/pipeline/", headers={"Authorization": f"Bearer {session_token}"})
    assert r2.status_code == 200


def test_login_rejects_wrong_password(client):
    r = client.post("/auth/login", json={"password": "nope"})
    assert r.status_code == 401


# ── Manual run gating ─────────────────────────────────────────────────────

def test_run_trigger_requires_auth(client):
    r = client.post("/runs/trigger", json={"trigger": "manual"})
    assert r.status_code == 401


def test_run_trigger_disabled_without_flag(client):
    # ALLOW_MANUAL_RUNS is unset in tests → manual runs must be refused.
    r = client.post("/runs/trigger", json={"trigger": "manual"}, headers=AUTH)
    assert r.status_code == 403


def test_run_trigger_enabled_with_flag(client, monkeypatch):
    monkeypatch.setenv("ALLOW_MANUAL_RUNS", "true")
    # Don't actually launch the crew — just verify the gate opens and a run row is recorded.
    from api.routes import runs as runs_module
    monkeypatch.setattr(runs_module, "_run_crew_in_thread", lambda run_id: None)
    r = client.post("/runs/trigger", json={"trigger": "manual"}, headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "running"
    assert body["trigger"] == "manual"


# ── Ingest validation & truthful statuses ─────────────────────────────────

def _ingest(client, apps):
    return client.post(
        "/ingest/applications",
        json={**INGEST, "applications": apps},
        headers=AUTH,
    )


def test_ingest_requires_bearer_token(client):
    r = client.post("/ingest/applications", json={**INGEST, "applications": []})
    assert r.status_code == 401


def test_ingest_rejects_wrong_secret(client):
    r = client.post(
        "/ingest/applications",
        json={"secret": "wrong", "applications": []},
        headers=AUTH,
    )
    # empty list short-circuits before the secret? No — secret is checked first.
    assert r.status_code == 403


def test_automation_cannot_set_applied(client):
    r = _ingest(client, [{
        "date_applied": "2026-07-01", "company": "TestCo Applied", "role": "Analyst",
        "url": "https://example.com/job/1", "status": "Applied",
    }])
    assert r.status_code == 200
    rows = client.get("/pipeline/", headers=AUTH).json()
    row = next(a for a in rows if a["company"] == "TestCo Applied")
    assert row["status"] == "Found"  # coerced — automation never marks Applied


def test_ingest_requires_company_and_role(client):
    r = _ingest(client, [
        {"date_applied": "2026-07-01", "company": "", "role": "Analyst"},
        {"date_applied": "2026-07-01", "company": "OnlyCo", "role": "  "},
    ])
    assert r.status_code == 200
    body = r.json()
    assert body["upserted"] == 0
    assert body["skipped"] == 2


def test_ingest_sets_validation_status_from_url(client):
    _ingest(client, [
        {"date_applied": "2026-07-01", "company": "VerifiedCo", "role": "Analyst",
         "url": "https://example.com/job/2", "status": "Found"},
        {"date_applied": "2026-07-01", "company": "NoUrlCo", "role": "Analyst",
         "status": "Found"},
    ])
    rows = client.get("/pipeline/", headers=AUTH).json()
    verified = next(a for a in rows if a["company"] == "VerifiedCo")
    unverified = next(a for a in rows if a["company"] == "NoUrlCo")
    assert verified["validation_status"] == "verified"
    assert unverified["validation_status"] == "unverified"


def test_ingest_deduplicates_by_company_role_url(client):
    job = {"date_applied": "2026-07-01", "company": "DupeCo", "role": "Analyst",
           "url": "https://example.com/job/3", "status": "Found"}
    _ingest(client, [job])
    _ingest(client, [{**job, "date_applied": "2026-07-02"}])  # same URL, later date
    rows = client.get("/pipeline/", headers=AUTH).json()
    dupes = [a for a in rows if a["company"] == "DupeCo"]
    assert len(dupes) == 1


def test_automation_never_downgrades_manual_status(client):
    job = {"date_applied": "2026-07-01", "company": "ManualCo", "role": "Analyst",
           "url": "https://example.com/job/4", "status": "Found"}
    _ingest(client, [job])
    rows = client.get("/pipeline/", headers=AUTH).json()
    app_id = next(a for a in rows if a["company"] == "ManualCo")["id"]

    # User manually marks it Applied (the only path that sets Applied).
    r = client.patch(f"/pipeline/{app_id}/status", json={"status": "Applied"}, headers=AUTH)
    assert r.status_code == 200

    # A later automated sync must not pull it back to Found.
    _ingest(client, [job])
    rows = client.get("/pipeline/", headers=AUTH).json()
    assert next(a for a in rows if a["company"] == "ManualCo")["status"] == "Applied"


# ── Pipeline status rules ─────────────────────────────────────────────────

def test_pipeline_rejects_invalid_status(client):
    _ingest(client, [{"date_applied": "2026-07-01", "company": "StatusCo", "role": "Analyst",
                      "url": "https://example.com/job/5", "status": "Found"}])
    rows = client.get("/pipeline/", headers=AUTH).json()
    app_id = next(a for a in rows if a["company"] == "StatusCo")["id"]
    r = client.patch(f"/pipeline/{app_id}/status", json={"status": "Auto-Applied"}, headers=AUTH)
    assert r.status_code == 400


def test_pipeline_accepts_new_truthful_statuses(client):
    rows = client.get("/pipeline/", headers=AUTH).json()
    app_id = next(a for a in rows if a["company"] == "StatusCo")["id"]
    for status in ["Drafted", "Ready to Apply", "Applied"]:
        r = client.patch(f"/pipeline/{app_id}/status", json={"status": status}, headers=AUTH)
        assert r.status_code == 200, f"{status} should be a valid manual status"


# ── Demo routes ───────────────────────────────────────────────────────────

def test_demo_routes_registered_outside_production(client):
    # ENV=test in the suite → demo seeding exists but still requires auth.
    r = client.post("/demo/seed")
    assert r.status_code == 401


def test_demo_routes_absent_in_production(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("PUBLIC_DEMO_MODE", raising=False)
    import api.main as main_module
    prod_app = importlib.reload(main_module).app
    paths = {getattr(route, "path", "") for route in prod_app.routes}
    assert not any(p.startswith("/demo") for p in paths)
    # Restore the module for any later imports.
    monkeypatch.setenv("ENV", "test")
    importlib.reload(main_module)
