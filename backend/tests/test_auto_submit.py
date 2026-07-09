"""
Offline tests for the auto_submit safety layer: ATS detection, gating rules,
and the reviewer's fail-closed parsing. No network, no Playwright, no LLM —
these lock in the guarantees (Optum never auto-submitted, caps enforced,
malformed reviewer output → REJECT) so a refactor can't silently weaken them.
"""
import pytest

from auto_submit.ats import detect_ats
from auto_submit.gating import GateContext, decide, is_internal
from auto_submit.reviewer import PLACEHOLDER_PATTERN, _parse_verdict


def job(**kw):
    base = {"company": "Databricks", "role": "Data Engineer",
            "url": "https://boards.greenhouse.io/databricks/jobs/1234567", "notes": ""}
    base.update(kw)
    return base


def auto_ctx(**kw):
    return GateContext(apply_mode="auto", **kw)


# ── ATS detection ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("url,expected", [
    ("https://boards.greenhouse.io/anthropic/jobs/4020295008", "greenhouse"),
    ("https://job-boards.greenhouse.io/dbtlabsinc/jobs/5555555", "greenhouse"),
    ("https://jobs.lever.co/acme/1b2c3d4e-1111-2222-3333-444455556666", "lever"),
    ("https://jobs.ashbyhq.com/openai/1b2c3d4e-1111-2222-3333-444455556666", "ashby"),
    ("https://careers.unitedhealthgroup.com/job/123456/data-analyst", None),
    ("https://www.linkedin.com/jobs/view/3456789", None),
    ("https://myworkdayjobs.com/acme/job/Data-Analyst_R1234", None),
    ("", None),
])
def test_detect_ats(url, expected):
    assert detect_ats(url) == expected


# ── Gating rules ────────────────────────────────────────────────────────────

def test_review_mode_never_auto():
    d = decide(job(), GateContext(apply_mode="review"), has_materials=True)
    assert d.action == "manual"


def test_internal_optum_hard_blocked():
    for company in ("Optum", "UnitedHealth Group", "OptumInsight", "Optum Health"):
        d = decide(job(company=company), auto_ctx(), has_materials=True)
        assert d.action == "manual"
        assert "internal" in d.reason.lower()


def test_internal_flag_in_notes_blocks():
    d = decide(job(notes="INTERNAL | $120k | SQL"), auto_ctx(), has_materials=True)
    assert d.action == "manual"


def test_is_internal_matches_variants():
    assert is_internal("Optum Health")
    assert is_internal("UNITEDHEALTH GROUP")
    assert not is_internal("Anthropic")


def test_duplicate_submission_skipped():
    ctx = auto_ctx(already_sent={("databricks", "data engineer")})
    d = decide(job(), ctx, has_materials=True)
    assert d.action == "skip"


def test_daily_cap_enforced():
    ctx = auto_ctx(max_per_day=2, submitted_today=2)
    d = decide(job(), ctx, has_materials=True)
    assert d.action == "manual"
    assert "cap" in d.reason


def test_missing_materials_blocks():
    d = decide(job(), auto_ctx(), has_materials=False)
    assert d.action == "manual"


def test_missing_url_blocks():
    d = decide(job(url=""), auto_ctx(), has_materials=True)
    assert d.action == "manual"


def test_clean_external_job_approved_for_auto():
    d = decide(job(), auto_ctx(), has_materials=True)
    assert d.action == "auto"


# ── Reviewer fail-closed parsing ────────────────────────────────────────────

def test_reviewer_rejects_non_json():
    assert _parse_verdict("I think this looks fine!")["verdict"] == "REJECT"


def test_reviewer_rejects_malformed_json():
    assert _parse_verdict('{"verdict": "APPROVE", "cover_letter": ')["verdict"] == "REJECT"


def test_reviewer_rejects_missing_verdict():
    assert _parse_verdict('{"cover_letter": "Dear team..."}')["verdict"] == "REJECT"


def test_reviewer_parses_valid_approve():
    v = _parse_verdict('{"verdict": "APPROVE", "reasons": [], "cover_letter": "Dear Databricks..."}')
    assert v["verdict"] == "APPROVE"
    assert v["cover_letter"].startswith("Dear")


def test_reviewer_strips_markdown_fences():
    v = _parse_verdict('```json\n{"verdict": "REJECT", "reasons": ["wrong company"]}\n```')
    assert v["verdict"] == "REJECT"


@pytest.mark.parametrize("text", [
    "I am excited to join [team] at Acme.",
    "As discussed, TBD metrics improved.",
    "My work at {{company}} shows...",
    "I led [insert project name] to success.",
])
def test_placeholder_pattern_catches_leftovers(text):
    assert PLACEHOLDER_PATTERN.search(text)


def test_placeholder_pattern_allows_clean_letter():
    clean = ("As a data analyst with five years at Optum, I improved audit throughput "
             "by 30% and built a Snowflake warehouse for claims analytics.")
    assert not PLACEHOLDER_PATTERN.search(clean)
