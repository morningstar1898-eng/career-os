"""
auto_submit/run_auto_submit.py
Orchestrates the auto-submit pipeline. Runs as a workflow step AFTER the crew
(so drafted materials exist) and BEFORE the briefing is posted/emailed (so the
report lands in both).

Per job found today:  gate → validate URL → reviewer approval → Playwright
submit (dry-run by default) → update the tracker Sheet → archive evidence.

Every outcome is written to submission_report.md, which clean_briefing.py
appends to the daily briefing — the email now answers "what was actually
submitted, with what proof" every single day.

Usage (from backend/): python -m auto_submit.run_auto_submit
"""
import base64
import json
import os
import re
import sys
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

from auto_submit.ats import validate_posting
from auto_submit.gating import (
    ALREADY_SENT_STATUSES, GateContext, decide, _norm,
)
from auto_submit.reviewer import review_application
from auto_submit.submitters import submit_application

load_dotenv()

TODAY = datetime.now().strftime("%Y-%m-%d")
REPORT_PATH = "submission_report.md"
SHEET_RANGE = "Sheet1!A:F"


def env_flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")


# ── Google Sheet helpers ────────────────────────────────────────────────────

def sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_JSON", "config/google_credentials.json"),
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds)


def read_rows(service) -> list[dict]:
    values = service.spreadsheets().values().get(
        spreadsheetId=os.getenv("GOOGLE_SHEET_ID"), range=SHEET_RANGE
    ).execute().get("values", [])
    if len(values) < 2:
        return []
    headers = [h.lower().replace(" ", "_") for h in values[0]]
    rows = []
    for idx, row in enumerate(values[1:], start=2):  # 1-based + header row
        obj = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        obj["_row"] = idx
        rows.append(obj)
    return rows


def update_row(service, row_num: int, status: str, note_suffix: str, old_notes: str):
    # Rows in the lookback window can be reprocessed on later runs — don't
    # append the same note twice.
    if note_suffix in (old_notes or ""):
        notes = old_notes
    else:
        notes = (old_notes + " | " if old_notes else "") + note_suffix
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=os.getenv("GOOGLE_SHEET_ID"),
        body={"valueInputOption": "USER_ENTERED", "data": [
            {"range": f"Sheet1!D{row_num}", "values": [[status]]},
            {"range": f"Sheet1!F{row_num}", "values": [[notes[:450]]]},
        ]},
    ).execute()


# ── Azure Blob helpers (materials in, evidence out) ─────────────────────────

def blob_container():
    from azure.storage.blob import BlobServiceClient
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn:
        return None
    client = BlobServiceClient.from_connection_string(conn)
    return client.get_container_client(os.getenv("AZURE_STORAGE_CONTAINER", "portfolio-charts"))


def slug(s: str) -> str:
    return (s or "").lower().replace(" ", "-").replace("/", "-")


def load_materials(container, company: str, role: str, date: str) -> str:
    """Find the SaveMaterialsTool blob for this company+role from the run that
    logged the row (rows from the lookback window may be older than today)."""
    if container is None:
        return ""
    prefix = f"application-materials/{date}/"
    company_slug, role_slug = slug(company), slug(role)[:50]
    best = None
    for blob in container.list_blobs(name_starts_with=prefix):
        name = blob.name[len(prefix):]
        if company_slug and company_slug in name:
            if best is None or role_slug[:20] in name:
                best = blob.name
    if not best:
        return ""
    return container.download_blob(best).readall().decode("utf-8", errors="replace")


def fetch_resume_pdf(container) -> str:
    """Resume PDF lives in the private blob container (too big for a GH secret)."""
    if container is None:
        return ""
    blob_name = os.getenv("RESUME_PDF_BLOB", "application-materials/resume/resume.pdf")
    local = "config/resume_for_submit.pdf"
    try:
        data = container.download_blob(blob_name).readall()
        os.makedirs("config", exist_ok=True)
        with open(local, "wb") as f:
            f.write(data)
        return local
    except Exception:
        return ""


def upload_evidence(container, local_path: str) -> str:
    if container is None or not os.path.exists(local_path):
        return ""
    blob_name = f"application-materials/{TODAY}/confirmations/{os.path.basename(local_path)}"
    with open(local_path, "rb") as f:
        container.upload_blob(blob_name, f, overwrite=True)
    return blob_name


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    apply_mode = os.getenv("APPLY_MODE", "review").strip().lower()
    dry_run = env_flag("AUTO_SUBMIT_DRY_RUN", "true")
    max_per_day = int(os.getenv("MAX_AUTO_SUBMITS_PER_DAY", "5"))

    report = [f"## Applications Report — {TODAY}",
              f"Mode: **{apply_mode}**" + (" (DRY RUN — forms filled, nothing submitted)" if dry_run and apply_mode == "auto" else "")]

    if apply_mode != "auto":
        report.append("Auto-submit is off (APPLY_MODE=review). All jobs await your manual review.")
        write_report(report)
        return

    profile, profile_err = load_profile()
    if not profile:
        report.append(f"⚠️ Applicant profile unavailable ({profile_err}) — cannot fill forms. All jobs left manual.")
        write_report(report)
        return

    service = sheets_service()
    rows = read_rows(service)
    # Process a small lookback window, not just today: a day where an agent
    # step flaked (no materials archived, no rows logged) self-heals on the
    # next run. Only automation-eligible statuses are picked up — "Ready to
    # Apply" is terminal (waiting on the user), submitted/manual rows never
    # re-enter.
    lookback = int(os.getenv("AUTO_SUBMIT_LOOKBACK_DAYS", "3"))
    window = {
        (datetime.now() - timedelta(days=d)).strftime("%Y-%m-%d")
        for d in range(lookback + 1)
    }
    candidate_rows = [
        r for r in rows
        if r.get("date_applied") in window and r.get("company")
        and _norm(r.get("status")) in ("found", "drafted")
    ]
    already_sent = {
        (_norm(r.get("company")), _norm(r.get("role")))
        for r in rows if _norm(r.get("status")) in ALREADY_SENT_STATUSES
    }

    container = blob_container()
    resume_pdf = fetch_resume_pdf(container)
    if not resume_pdf:
        report.append("⚠️ Resume PDF not found in blob storage (RESUME_PDF_BLOB) — cannot submit. All jobs left manual.")
        write_report(report)
        return

    resume_text = ""
    try:
        with open(os.getenv("RESUME_PATH", "config/resume.txt"), encoding="utf-8") as f:
            resume_text = f.read()
    except FileNotFoundError:
        pass
    if len(resume_text) < 500:
        # Without the real resume the reviewer can't verify truthfulness —
        # the run that drafted fabricated materials was exactly a no-resume
        # run. Nothing auto-submits on a day like that.
        report.append("⚠️ Resume text unavailable — reviewer cannot verify claims. All jobs left manual.")
        write_report(report)
        return

    ctx = GateContext(apply_mode=apply_mode, max_per_day=max_per_day, already_sent=already_sent)
    os.makedirs("outputs", exist_ok=True)

    for job in candidate_rows:
        company, role = job.get("company", ""), job.get("role", "")
        tag = f"**{company} — {role}**"
        materials = load_materials(container, company, role, job.get("date_applied", TODAY))

        gate = decide(job, ctx, has_materials=bool(materials))
        if gate.action == "skip":
            report.append(f"- ⏭️ {tag}: skipped — {gate.reason}")
            continue
        if gate.action == "manual":
            mark_manual(service, job, gate.reason, report, tag)
            continue

        posting = validate_posting(job.get("url", ""))
        if not posting["ok"]:
            mark_manual(service, job, f"URL check failed: {posting['reason']}", report, tag)
            continue

        verdict = review_application(job, posting["page_text"], materials, resume_text)
        if verdict["verdict"] != "APPROVE":
            reasons = "; ".join(verdict["reasons"])[:200]
            mark_manual(service, job, f"reviewer held it: {reasons}", report, tag)
            continue

        shot = f"outputs/{slug(company)}--{slug(role)[:40]}.png"
        result = submit_application(
            ats=posting["ats"], url=posting["final_url"], profile=profile,
            resume_pdf_path=resume_pdf, cover_letter=verdict["cover_letter"],
            screenshot_path=shot, dry_run=dry_run,
        )
        evidence = upload_evidence(container, result.screenshot_path)

        if result.outcome == "submitted":
            ctx.submitted_today += 1
            update_row(service, job["_row"], "Submitted (auto)",
                       f"auto-submitted {TODAY}; reviewer-approved; confirmation: "
                       f"'{result.confirmation_text[:80]}'; evidence: {evidence}", job.get("notes", ""))
            report.append(f"- ✅ {tag}: **SUBMITTED** — confirmation captured "
                          f"(\"{result.confirmation_text[:100]}\")")
        elif result.outcome == "dry_run_ok":
            ctx.submitted_today += 1  # count against cap so live behavior matches
            # Stays "Drafted" (not "Ready to Apply") so the row remains
            # automation-eligible — it submits for real once dry-run is off.
            update_row(service, job["_row"], "Drafted",
                       f"DRY RUN passed {TODAY} — form filled OK, reviewer approved; "
                       f"screenshot: {evidence}. Set AUTO_SUBMIT_DRY_RUN=false to go live.",
                       job.get("notes", ""))
            report.append(f"- 🧪 {tag}: dry run PASSED — reviewer approved, form filled, screenshot saved")
        else:
            mark_manual(service, job, f"submit aborted: {result.detail}", report, tag,
                        extra_evidence=evidence)

    submitted = sum(1 for line in report if "SUBMITTED" in line)
    passed = sum(1 for line in report if "dry run PASSED" in line)
    manual = sum(1 for line in report if line.startswith("- 👤"))
    report.insert(2, f"Summary: {submitted} submitted, {passed} dry-run passed, {manual} left for manual apply.")
    write_report(report)


def mark_manual(service, job, reason: str, report: list, tag: str, extra_evidence: str = ""):
    note = f"auto-submit: {reason}"
    if extra_evidence:
        note += f"; evidence: {extra_evidence}"
    try:
        update_row(service, job["_row"], "Ready to Apply", note, job.get("notes", ""))
    except Exception as e:
        print(f"sheet update failed for {tag}: {e}", file=sys.stderr)
    report.append(f"- 👤 {tag}: manual apply — {reason}")


def load_profile() -> tuple[dict, str]:
    """Returns (profile, error). Strips a leading UTF-8 BOM — PowerShell pipes
    add one when setting the secret, and it silently breaks json.loads (the
    same BOM class of bug main.py patches globally for CrewAI tool calls)."""
    raw = os.getenv("APPLICANT_PROFILE_JSON", "")
    if not raw:
        try:
            with open("config/applicant_profile.json", encoding="utf-8-sig") as f:
                raw = f.read()
        except FileNotFoundError:
            return {}, "APPLICANT_PROFILE_JSON secret not set"
    raw = raw.lstrip("﻿").strip()
    try:
        profile = json.loads(raw)
    except json.JSONDecodeError as e:
        return {}, f"profile JSON does not parse ({e.msg} at char {e.pos})"
    if not isinstance(profile, dict) or not profile.get("email"):
        return {}, "profile JSON parsed but is missing 'email'"
    return profile, ""


def write_report(lines: list) -> None:
    text = "\n".join(lines) + "\n"
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
