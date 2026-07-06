"""
Gmail integration scaffold — consent-first, career-search-focused, revocable.

What is implemented now:
- Explicit connect/disconnect with a consent record and full data deletion.
- Keyword-based classification of job-search emails (testable without Gmail).
- Safe pipeline updates: confirmed events move applications forward and every
  change is recorded in application_events — manual statuses are never
  silently overwritten (history preserves both).

What is scaffolded (requires GMAIL_CLIENT_ID/SECRET/REDIRECT_URI):
- The OAuth URL builder and callback. Real token exchange + targeted Gmail
  API queries (metadata-first, never a blind full-mailbox scan) are the next
  implementation step — see docs/GMAIL_INTEGRATION.md.

Privacy rules enforced here:
- Only Pro/Premium plans can connect (server-side entitlement).
- Full email bodies are never stored — only extracted events and snippets.
- DISABLE_GMAIL_SYNC kill switch stops all sync activity.
"""
import json
import logging
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api import config
from api.db import get_db
from api.saas import plans, usage
from api.saas.deps import get_current_user
from api.saas.routes.jobs import record_event

router = APIRouter()
logger = logging.getLogger("career_os.saas.gmail")

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

CONSENT_TEXT = {
    "what_we_use_gmail_for": [
        "Detecting job-search events: application confirmations, interview invitations, "
        "rejections, recruiter outreach, assessments, and offers.",
        "Updating your application pipeline automatically from those events.",
    ],
    "what_we_do_not_do": [
        "We do not read or store your general email.",
        "We do not store full email bodies — only extracted job-search events and short snippets.",
        "We never send email on your behalf without your explicit approval of each message.",
        "We use targeted job-search queries, not a full mailbox scan.",
    ],
    "how_to_disconnect": "POST /v1/gmail/disconnect at any time (also revoke at myaccount.google.com/permissions).",
    "how_to_delete_data": "DELETE /v1/gmail/events removes every imported event immediately.",
}

# event_type → pipeline status it may move an application to
EVENT_STATUS_MAP = {
    "application_confirmation": "Confirmation Received",
    "rejection": "Rejected",
    "interview_invitation": "Interview",
    "recruiter_message": "Recruiter Screen",
    "assessment": "Assessment",
    "offer": "Offer",
}

# Statuses a Gmail event may move an application FROM (never regress a later stage)
STATUS_RANK = {
    "Found": 0, "Saved": 0, "Drafted": 1, "Ready to Apply": 2, "Applied": 3,
    "Confirmation Received": 4, "Recruiter Screen": 5, "Assessment": 6,
    "Interview": 7, "Offer": 8, "Rejected": 9, "Ghosted": 9, "Withdrawn": 9,
}


class EmailMessage(BaseModel):
    """A candidate job-search email (metadata + snippet only — no full body)."""
    gmail_message_id: str
    thread_id: str | None = None
    sender: str = ""
    subject: str = ""
    snippet: str = ""
    received_at: str | None = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_email(subject: str, snippet: str = "", sender: str = "") -> tuple[str, float]:
    """Keyword-based classification of a job-search email.
    Returns (event_type, confidence). Deterministic and unit-tested; an AI
    classifier can replace this behind the same signature later."""
    text = f"{subject} {snippet}".lower()

    rules = [
        ("offer", 0.85, ["offer letter", "pleased to offer", "extend an offer", "job offer"]),
        ("rejection", 0.85, ["not to move forward", "decided to move forward with other",
                             "unfortunately", "no longer under consideration", "not been selected",
                             "pursue other candidates"]),
        ("interview_invitation", 0.85, ["schedule an interview", "interview invitation",
                                        "like to interview", "phone interview", "video interview",
                                        "onsite interview", "schedule a call with the team"]),
        ("assessment", 0.8, ["assessment", "coding challenge", "take-home", "hackerrank",
                             "codesignal", "technical screen test"]),
        ("application_confirmation", 0.8, ["application received", "thank you for applying",
                                           "we received your application", "application confirmation",
                                           "successfully submitted"]),
        ("recruiter_message", 0.6, ["recruiter", "talent acquisition", "sourcing", "opportunity at",
                                    "your background", "came across your profile"]),
        ("follow_up_needed", 0.5, ["following up", "checking in", "any update"]),
    ]
    for event_type, confidence, keywords in rules:
        if any(k in text for k in keywords):
            return event_type, confidence
    if any(k in text for k in ["application", "position", "role", "job", "career"]):
        return "unknown_career_related", 0.3
    return "unknown_career_related", 0.1


def _find_matching_application(conn, user_id: int, sender: str, subject: str, snippet: str):
    """Match an email to an application by company name appearing in the text."""
    text = f"{sender} {subject} {snippet}".lower()
    rows = conn.execute(
        "SELECT a.id, a.status, j.company, j.role FROM saas_applications a "
        "JOIN saas_jobs j ON a.job_id = j.id WHERE a.user_id = ?",
        (user_id,),
    ).fetchall()
    best = None
    for r in rows:
        company = (r["company"] or "").lower()
        if company and len(company) >= 3 and company in text:
            if best is None or len(company) > len((best["company"] or "")):
                best = r
    return best


# ── Connection lifecycle ──────────────────────────────────

@router.get("/gmail/status")
def gmail_status(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        row = conn.execute(
            "SELECT status, google_email, connected_at, last_sync_at FROM gmail_connections "
            "WHERE user_id = ?", (user["id"],),
        ).fetchone()
        events = conn.execute(
            "SELECT COUNT(*) FROM email_events WHERE user_id = ?", (user["id"],)
        ).fetchone()[0]
    return {
        "connected": bool(row and row["status"] == "connected"),
        "google_email": row["google_email"] if row else None,
        "connected_at": row["connected_at"] if row else None,
        "last_sync_at": row["last_sync_at"] if row else None,
        "imported_events": events,
        "configured": config.gmail_configured(),
        "sync_disabled": config.disable_gmail_sync(),
        "consent": CONSENT_TEXT,
    }


@router.post("/gmail/connect")
def gmail_connect(user: dict = Depends(get_current_user)):
    """Step 1: entitlement check + consent + OAuth URL. The user must visit
    the returned URL and grant access; nothing is read until they do."""
    plans.require_entitlement(user, "can_connect_gmail")
    if config.disable_gmail_sync():
        raise HTTPException(503, "Gmail sync is temporarily disabled by the administrator.")
    if not config.gmail_configured():
        raise HTTPException(
            501,
            "Gmail OAuth is not configured on this deployment "
            "(GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET / GMAIL_REDIRECT_URI).",
        )
    params = urllib.parse.urlencode({
        "client_id": config.gmail_client_id(),
        "redirect_uri": config.gmail_redirect_uri(),
        "response_type": "code",
        "scope": GMAIL_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": f"user-{user['id']}",
    })
    return {
        "consent": CONSENT_TEXT,
        "authorization_url": f"https://accounts.google.com/o/oauth2/v2/auth?{params}",
        "note": "Visit authorization_url to grant read-only access. Token exchange happens in the callback.",
    }


@router.post("/gmail/callback")
def gmail_callback(body: dict, user: dict = Depends(get_current_user)):
    """Step 2 (scaffold): record the connection. The real deployment exchanges
    body['code'] for tokens via Google's token endpoint — see
    docs/GMAIL_INTEGRATION.md for the completion checklist."""
    plans.require_entitlement(user, "can_connect_gmail")
    if not config.gmail_configured():
        raise HTTPException(501, "Gmail OAuth is not configured on this deployment.")
    code = (body.get("code") or "").strip()
    if not code:
        raise HTTPException(400, "Missing authorization code")

    now = _now()
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM gmail_connections WHERE user_id = ?", (user["id"],)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE gmail_connections SET status = 'connected', scopes = ?, connected_at = ?, "
                "disconnected_at = NULL WHERE user_id = ?",
                (GMAIL_SCOPE, now, user["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO gmail_connections (user_id, status, scopes, connected_at) "
                "VALUES (?, 'connected', ?, ?)",
                (user["id"], GMAIL_SCOPE, now),
            )
    logger.info("gmail connected: user_id=%s", user["id"])
    return {"status": "connected",
            "note": "Scaffold: token exchange with Google is the next implementation step."}


@router.post("/gmail/disconnect")
def gmail_disconnect(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        conn.execute(
            "UPDATE gmail_connections SET status = 'disconnected', refresh_token = NULL, "
            "disconnected_at = ? WHERE user_id = ?",
            (_now(), user["id"]),
        )
    logger.info("gmail disconnected: user_id=%s", user["id"])
    return {"status": "disconnected",
            "note": "Also revoke access at myaccount.google.com/permissions. "
                    "Imported events remain until you DELETE /v1/gmail/events."}


@router.delete("/gmail/events")
def delete_gmail_events(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM email_events WHERE user_id = ?", (user["id"],))
    return {"status": "deleted", "events_removed": cursor.rowcount}


@router.get("/gmail/events")
def list_gmail_events(user: dict = Depends(get_current_user)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM email_events WHERE user_id = ? ORDER BY id DESC LIMIT 100",
            (user["id"],),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Event ingestion + safe pipeline updates ───────────────

@router.post("/gmail/events/ingest")
def ingest_email_event(msg: EmailMessage, user: dict = Depends(get_current_user)):
    """Classify one job-search email and update the pipeline safely.
    Called by the (future) sync worker with real Gmail messages; callable
    directly for testing and manual import. Requires Gmail entitlement."""
    plans.require_entitlement(user, "can_connect_gmail")
    if config.disable_gmail_sync():
        raise HTTPException(503, "Gmail sync is temporarily disabled by the administrator.")
    usage.check_and_increment(user, "gmail_scans")

    event_type, confidence = classify_email(msg.subject, msg.snippet, msg.sender)
    now = _now()

    with get_db() as conn:
        dupe = conn.execute(
            "SELECT id FROM email_events WHERE user_id = ? AND gmail_message_id = ?",
            (user["id"], msg.gmail_message_id),
        ).fetchone()
        if dupe:
            return {"status": "duplicate", "event_id": dupe["id"]}

        matched = _find_matching_application(conn, user["id"], msg.sender, msg.subject, msg.snippet)
        application_id = matched["id"] if matched else None

        cursor = conn.execute(
            "INSERT INTO email_events (user_id, gmail_message_id, thread_id, sender, subject, "
            "received_at, event_type, company, role, application_id, confidence_score, "
            "snippet_or_summary, action_needed, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user["id"], msg.gmail_message_id, msg.thread_id, msg.sender[:200], msg.subject[:300],
             msg.received_at, event_type, matched["company"] if matched else None,
             matched["role"] if matched else None, application_id, confidence,
             msg.snippet[:500], "review" if event_type == "follow_up_needed" else None, now),
        )
        event_id = cursor.lastrowid

        status_changed = None
        if matched and event_type in EVENT_STATUS_MAP and confidence >= 0.6:
            new_status = EVENT_STATUS_MAP[event_type]
            current = matched["status"]
            # Never regress a later stage; never silently overwrite — the event
            # history records everything either way.
            if STATUS_RANK.get(new_status, 0) > STATUS_RANK.get(current, 0):
                conn.execute(
                    "UPDATE saas_applications SET status = ?, last_event_date = ?, updated_at = ? "
                    "WHERE id = ? AND user_id = ?",
                    (new_status, now, now, matched["id"], user["id"]),
                )
                record_event(conn, user["id"], matched["id"], "gmail_event",
                             current, new_status,
                             "gmail", f"{event_type} (confidence {confidence}): {msg.subject[:100]}")
                status_changed = new_status
            else:
                record_event(conn, user["id"], matched["id"], "gmail_event",
                             current, current, "gmail",
                             f"{event_type} detected but status kept (already at/after this stage)")

    return {
        "status": "ok", "event_id": event_id, "event_type": event_type,
        "confidence": confidence, "matched_application_id": application_id,
        "application_status_changed_to": status_changed,
    }
