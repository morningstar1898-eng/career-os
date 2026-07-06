"""
SaaS foundation tests: accounts, trial, entitlements, per-user data isolation,
Gmail event classification + safe pipeline updates, assist approval flow,
admin role enforcement, and the Stripe webhook.
"""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone


def _signup(client, email, password="longpassword123"):
    return client.post("/v1/auth/signup", json={"email": email, "password": password})


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _user(client, email):
    """Create a user and return (token, user_id, headers)."""
    r = _signup(client, email)
    assert r.status_code == 200, r.text
    body = r.json()
    return body["token"], body["user_id"], _auth(body["token"])


def _set_plan(user_id, plan, sub_status="active"):
    from api.db import get_db
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET plan = ?, subscription_status = ?, status = 'active' WHERE id = ?",
            (plan, sub_status, user_id),
        )


def _expire_trial(user_id):
    from api.db import get_db
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET trial_ends_at = ?, subscription_status = NULL WHERE id = ?",
            (past, user_id),
        )


PROFILE = {
    "target_roles": ["Data Analyst", "Analytics Engineer"],
    "current_skills": ["SQL", "Excel"],
    "target_locations": ["Remote"],
    "remote_preference": "remote",
}

JOB = {
    "company": "Nimbus Data Co.",
    "role": "Data Analyst",
    "canonical_url": "https://example.com/careers/da-1",
    "description": "We need SQL, Python, dbt, and Airflow experience. Snowflake a plus.",
}


# ── Accounts & trial ──────────────────────────────────────

def test_signup_starts_3_day_trial(client):
    token, user_id, headers = _user(client, "trial1@test.local")
    me = client.get("/v1/me", headers=headers).json()
    assert me["plan"] == "trial"
    assert me["trial_active"] is True
    ends = datetime.fromisoformat(me["trial_ends_at"])
    delta = ends - datetime.now(timezone.utc)
    assert timedelta(days=2, hours=23) < delta < timedelta(days=3, hours=1)


def test_signup_requires_valid_email_and_password(client):
    assert _signup(client, "not-an-email").status_code == 400
    assert _signup(client, "short@test.local", "short").status_code == 400


def test_duplicate_signup_rejected(client):
    _user(client, "dupe@test.local")
    assert _signup(client, "dupe@test.local").status_code == 409


def test_disable_new_signups_flag(client, monkeypatch):
    monkeypatch.setenv("DISABLE_NEW_SIGNUPS", "true")
    assert _signup(client, "blocked@test.local").status_code == 503


def test_login_and_wrong_password(client):
    _user(client, "login1@test.local")
    ok = client.post("/v1/auth/login", json={"email": "login1@test.local", "password": "longpassword123"})
    assert ok.status_code == 200
    bad = client.post("/v1/auth/login", json={"email": "login1@test.local", "password": "wrongpassword1"})
    assert bad.status_code == 401


def test_saas_routes_require_session_token(client):
    assert client.get("/v1/me").status_code == 401
    assert client.get("/v1/jobs").status_code == 401
    # The legacy static API token is NOT a user session
    r = client.get("/v1/me", headers={"Authorization": "Bearer test-token"})
    assert r.status_code == 401


def test_expired_trial_blocks_paid_features_but_allows_login(client):
    token, user_id, headers = _user(client, "expired@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    r = client.post("/v1/jobs", json=JOB, headers=headers)
    job_id = r.json()["job_id"]

    _expire_trial(user_id)
    me = client.get("/v1/me", headers=headers).json()
    assert me["plan"] == "free_demo"
    assert me["trial_active"] is False

    # Paid feature blocked with 402
    r = client.post(f"/v1/jobs/{job_id}/score", headers=headers)
    assert r.status_code == 402

    # But the user can still export and delete their data
    assert client.get("/v1/me/export", headers=headers).status_code == 200


# ── Data isolation ────────────────────────────────────────

def test_user_cannot_see_another_users_data(client):
    _, id_a, headers_a = _user(client, "isolation-a@test.local")
    _, id_b, headers_b = _user(client, "isolation-b@test.local")

    client.put("/v1/profile", json=PROFILE, headers=headers_a)
    r = client.post("/v1/jobs", json={**JOB, "company": "SecretCo A"}, headers=headers_a)
    job_id = r.json()["job_id"]
    app_id = r.json()["application_id"]

    # B sees an empty world and gets 404 on A's resources
    assert client.get("/v1/jobs", headers=headers_b).json() == []
    assert client.get(f"/v1/jobs/{job_id}", headers=headers_b).status_code == 404
    assert client.get("/v1/applications", headers=headers_b).json() == []
    assert client.patch(f"/v1/applications/{app_id}/status",
                        json={"status": "Applied"}, headers=headers_b).status_code == 404
    assert client.get(f"/v1/applications/{app_id}/events", headers=headers_b).status_code == 404

    # B's export contains nothing of A's
    export_b = client.get("/v1/me/export", headers=headers_b).json()
    assert export_b["saas_jobs"] == []


def test_resume_isolation(client):
    _, _, headers_a = _user(client, "resume-a@test.local")
    _, _, headers_b = _user(client, "resume-b@test.local")
    r = client.post("/v1/resumes", json={"name": "R", "content": "Private resume text A"}, headers=headers_a)
    rid = r.json()["resume_id"]
    assert client.get(f"/v1/resumes/{rid}", headers=headers_b).status_code == 404
    assert client.delete(f"/v1/resumes/{rid}", headers=headers_b).status_code == 404


# ── Jobs, validation, truthful statuses ───────────────────

def test_job_without_url_is_unverified_and_not_found_status(client):
    _, _, headers = _user(client, "jobs1@test.local")
    r = client.post("/v1/jobs", json={"company": "NoUrl Inc", "role": "Analyst"}, headers=headers)
    body = r.json()
    assert body["validation_status"] == "unverified"
    assert body["initial_status"] == "Saved"      # only verified postings start as Found

    r2 = client.post("/v1/jobs", json=JOB, headers=headers)
    assert r2.json()["validation_status"] == "verified"
    assert r2.json()["initial_status"] == "Found"


def test_job_duplicate_detection(client):
    _, _, headers = _user(client, "jobs2@test.local")
    first = client.post("/v1/jobs", json=JOB, headers=headers).json()
    second = client.post("/v1/jobs", json=JOB, headers=headers).json()
    assert second["status"] == "duplicate"
    assert second["job_id"] == first["job_id"]


def test_fit_score_labeled_as_guidance(client):
    _, _, headers = _user(client, "fit1@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    job_id = client.post("/v1/jobs", json=JOB, headers=headers).json()["job_id"]
    details = client.post(f"/v1/jobs/{job_id}/score", headers=headers).json()
    assert 0 <= details["overall_fit_score"] <= 1
    assert "SQL" in details["matched_required_skills"]
    assert "dbt" in details["missing_required_skills"]
    assert "guidance" in details["reasoning_summary"].lower()


def test_manual_status_change_records_history(client):
    _, _, headers = _user(client, "hist1@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    app_id = client.post("/v1/jobs", json=JOB, headers=headers).json()["application_id"]
    client.patch(f"/v1/applications/{app_id}/status", json={"status": "Applied"}, headers=headers)
    events = client.get(f"/v1/applications/{app_id}/events", headers=headers).json()
    assert events[-1]["to_status"] == "Applied"
    assert events[-1]["source"] == "manual"


# ── Usage limits ──────────────────────────────────────────

def test_daily_usage_limit_enforced(client):
    _, user_id, headers = _user(client, "limits@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    job_id = client.post("/v1/jobs", json=JOB, headers=headers).json()["job_id"]
    # trial: max_job_matches_per_day = 10
    for _ in range(10):
        assert client.post(f"/v1/jobs/{job_id}/score", headers=headers).status_code == 200
    assert client.post(f"/v1/jobs/{job_id}/score", headers=headers).status_code == 429


# ── Skills & teaching moments ─────────────────────────────

def test_skill_gap_analysis_and_teaching_moment(client):
    _, _, headers = _user(client, "skills1@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    client.post("/v1/jobs", json=JOB, headers=headers)
    gaps = client.post("/v1/skills/analyze", headers=headers).json()["gaps"]
    gap_skills = {g["skill"] for g in gaps}
    assert "dbt" in gap_skills and "Airflow" in gap_skills
    assert "SQL" not in gap_skills  # user has SQL

    tm = client.post("/v1/teaching-moments", json={"skill": "dbt"}, headers=headers).json()
    assert tm["skill_gap"] == "dbt"
    assert tm["practice_task"]
    assert "only add once true" in tm["resume_bullet_after_completion"].lower() \
        or "after you actually complete" in tm["resume_bullet_after_completion"].lower()


# ── Gmail scaffold ────────────────────────────────────────

def test_trial_user_cannot_connect_gmail(client):
    _, _, headers = _user(client, "gmail-trial@test.local")
    assert client.post("/v1/gmail/connect", headers=headers).status_code == 403


def test_gmail_classification():
    from api.saas.routes.gmail import classify_email
    assert classify_email("Thank you for applying to Acme")[0] == "application_confirmation"
    assert classify_email("Update on your application", "we have decided to move forward with other candidates")[0] == "rejection"
    assert classify_email("Invitation to schedule an interview")[0] == "interview_invitation"
    assert classify_email("Your HackerRank assessment")[0] == "assessment"
    assert classify_email("We are pleased to offer you the position")[0] == "offer"


def test_gmail_event_updates_pipeline_safely(client):
    _, user_id, headers = _user(client, "gmail-pro@test.local")
    _set_plan(user_id, "pro")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    created = client.post("/v1/jobs", json=JOB, headers=headers).json()
    app_id = created["application_id"]
    client.patch(f"/v1/applications/{app_id}/status", json={"status": "Applied"}, headers=headers)

    r = client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "msg-1",
        "sender": "careers@nimbusdata.co",
        "subject": "Thank you for applying to Nimbus Data Co.",
        "snippet": "We received your application for Data Analyst",
    }, headers=headers)
    body = r.json()
    assert body["event_type"] == "application_confirmation"
    assert body["application_status_changed_to"] == "Confirmation Received"

    # A later, lower-stage event never regresses the status
    r2 = client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "msg-2",
        "sender": "careers@nimbusdata.co",
        "subject": "Nimbus Data Co. interview invitation — schedule an interview",
    }, headers=headers)
    assert r2.json()["application_status_changed_to"] == "Interview"

    r3 = client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "msg-3",
        "sender": "careers@nimbusdata.co",
        "subject": "Thank you for applying to Nimbus Data Co.",
        "snippet": "application received",
    }, headers=headers)
    assert r3.json()["application_status_changed_to"] is None  # kept at Interview

    events = client.get(f"/v1/applications/{app_id}/events", headers=headers).json()
    assert any(e["source"] == "gmail" for e in events)

    # Duplicate message id is idempotent
    dup = client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "msg-1", "subject": "Thank you for applying",
    }, headers=headers)
    assert dup.json()["status"] == "duplicate"


def test_gmail_kill_switch(client, monkeypatch):
    _, user_id, headers = _user(client, "gmail-kill@test.local")
    _set_plan(user_id, "pro")
    monkeypatch.setenv("DISABLE_GMAIL_SYNC", "true")
    r = client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "x", "subject": "any"}, headers=headers)
    assert r.status_code == 503


def test_gmail_disconnect_and_event_deletion(client):
    _, user_id, headers = _user(client, "gmail-del@test.local")
    _set_plan(user_id, "pro")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    client.post("/v1/jobs", json=JOB, headers=headers)
    client.post("/v1/gmail/events/ingest", json={
        "gmail_message_id": "del-1", "subject": "Thank you for applying to Nimbus Data Co."},
        headers=headers)
    assert client.get("/v1/gmail/status", headers=headers).json()["imported_events"] == 1
    r = client.delete("/v1/gmail/events", headers=headers)
    assert r.json()["events_removed"] == 1


# ── Application assistance (Premium, explicit approval) ───

def test_assist_requires_premium(client):
    _, _, headers = _user(client, "assist-trial@test.local")
    r = client.post("/v1/assist/package", json={"application_id": 1}, headers=headers)
    assert r.status_code == 403


def test_assist_package_and_explicit_confirmation(client):
    _, user_id, headers = _user(client, "assist-prem@test.local")
    _set_plan(user_id, "premium")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    app_id = client.post("/v1/jobs", json=JOB, headers=headers).json()["application_id"]

    pkg = client.post("/v1/assist/package", json={"application_id": app_id}, headers=headers).json()
    assert pkg["package"]["submission"].startswith("manual")
    assert pkg["package"]["apply_link"] == JOB["canonical_url"]

    # Without explicit confirmation, nothing moves to Applied
    r = client.post("/v1/assist/confirm-applied",
                    json={"application_id": app_id, "user_confirmed": False}, headers=headers)
    assert r.status_code == 400
    apps = client.get("/v1/applications", headers=headers).json()
    assert apps[0]["status"] != "Applied"

    # With explicit confirmation it does, and the audit trail shows it
    r = client.post("/v1/assist/confirm-applied",
                    json={"application_id": app_id, "user_confirmed": True}, headers=headers)
    assert r.json()["new_status"] == "Applied"
    audit = client.get("/v1/assist/audit", headers=headers).json()
    actions = {a["action"]: a for a in audit}
    assert actions["confirm_applied"]["user_confirmed"] == 1
    assert "confirm_applied_rejected" in actions


def test_assist_kill_switch(client, monkeypatch):
    _, user_id, headers = _user(client, "assist-kill@test.local")
    _set_plan(user_id, "premium")
    monkeypatch.setenv("DISABLE_APPLICATION_ASSIST", "true")
    r = client.post("/v1/assist/package", json={"application_id": 1}, headers=headers)
    assert r.status_code == 503


# ── Admin ─────────────────────────────────────────────────

def test_admin_routes_require_admin_role(client):
    _, _, headers = _user(client, "notadmin@test.local")
    assert client.get("/v1/admin/overview", headers=headers).status_code == 403
    assert client.get("/v1/admin/users", headers=headers).status_code == 403


def test_admin_bootstrap_via_admin_email(client):
    token, _, headers = _user(client, "admin@test.local")  # matches ADMIN_EMAIL
    overview = client.get("/v1/admin/overview", headers=headers)
    assert overview.status_code == 200
    assert "users" in overview.json()
    assert "feature_flags" in overview.json()


# ── Feedback ──────────────────────────────────────────────

def test_feedback_submission(client):
    _, _, headers = _user(client, "feedback@test.local")
    r = client.post("/v1/feedback", json={"area": "job_match", "rating": "useful",
                                          "comment": "good match"}, headers=headers)
    assert r.status_code == 200
    bad = client.post("/v1/feedback", json={"area": "nonsense"}, headers=headers)
    assert bad.status_code == 400


# ── Billing webhook ───────────────────────────────────────

def _stripe_sig(payload: bytes, secret: str) -> str:
    t = str(int(time.time()))
    signed = f"{t}.".encode() + payload
    v1 = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return f"t={t},v1={v1}"


def test_webhook_rejects_bad_signature(client):
    r = client.post("/v1/billing/webhook", content=b"{}",
                    headers={"stripe-signature": "t=1,v1=bad"})
    assert r.status_code == 400


def test_webhook_upgrades_plan_server_side(client):
    _, user_id, headers = _user(client, "stripe@test.local")
    from api.db import get_db
    with get_db() as conn:
        conn.execute("UPDATE users SET stripe_customer_id = 'cus_test1' WHERE id = ?", (user_id,))

    event = {
        "id": "evt_test_1",
        "type": "customer.subscription.created",
        "data": {"object": {
            "id": "sub_test1", "customer": "cus_test1", "status": "active",
            "items": {"data": [{"price": {"id": "price_pro_test"}}]},
        }},
    }
    payload = json.dumps(event).encode()
    r = client.post("/v1/billing/webhook", content=payload,
                    headers={"stripe-signature": _stripe_sig(payload, "whsec_test")})
    assert r.status_code == 200 and r.json()["handled"] is True

    me = client.get("/v1/me", headers=headers).json()
    assert me["plan"] == "pro"
    assert me["entitlements"]["can_connect_gmail"] is True

    # Replay is idempotent
    r2 = client.post("/v1/billing/webhook", content=payload,
                     headers={"stripe-signature": _stripe_sig(payload, "whsec_test")})
    assert r2.json()["status"] == "already_processed"


def test_checkout_not_faked_without_stripe_key(client):
    _, _, headers = _user(client, "checkout@test.local")
    r = client.post("/v1/billing/checkout", json={"plan": "pro"}, headers=headers)
    assert r.status_code == 501  # scaffolded, never a fake success


# ── Account deletion ──────────────────────────────────────

def test_account_deletion_wipes_data(client):
    _, user_id, headers = _user(client, "gdpr@test.local")
    client.put("/v1/profile", json=PROFILE, headers=headers)
    client.post("/v1/resumes", json={"name": "R", "content": "private"}, headers=headers)
    client.post("/v1/jobs", json=JOB, headers=headers)

    assert client.delete("/v1/me", headers=headers).json()["status"] == "deleted"
    # Session no longer works
    assert client.get("/v1/me", headers=headers).status_code == 401

    from api.db import get_db
    with get_db() as conn:
        for table in ("career_profiles", "resumes", "saas_jobs", "saas_applications"):
            count = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (user_id,)).fetchone()[0]
            assert count == 0, f"{table} not wiped"
        email = conn.execute("SELECT email FROM users WHERE id = ?", (user_id,)).fetchone()[0]
        assert "deleted" in email
