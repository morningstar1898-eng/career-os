"""
sync_applications.py
Reads today's job applications from Google Sheets and POSTs them to the
/ingest/applications API endpoint so the pipeline Kanban stays in sync.
Called as a workflow step after agents run.
"""
import os
import json
import sys
import requests
from datetime import datetime
from googleapiclient.discovery import build
from tools.google_creds import load_google_credentials

TODAY = datetime.now().strftime("%Y-%m-%d")
API_URL = os.getenv("API_URL", "").rstrip("/")
INGEST_SECRET = os.getenv("INGEST_SECRET", "")
SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
CREDS_PATH = os.getenv("GOOGLE_CREDENTIALS_JSON", "config/google_credentials.json")


def read_sheet() -> list[dict]:
    creds = load_google_credentials(
        CREDS_PATH,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=creds)
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A:F"
    ).execute()
    values = result.get("values", [])
    if not values or len(values) < 2:
        return []
    headers = [h.lower().replace(" ", "_") for h in values[0]]
    return [
        {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
        for row in values[1:]
    ]


def main():
    if not API_URL or not INGEST_SECRET or not SHEET_ID:
        print("sync_applications: missing API_URL, INGEST_SECRET, or GOOGLE_SHEET_ID — skipping")
        return

    rows = read_sheet()
    today_rows = [r for r in rows if r.get("date_applied", "") == TODAY]
    if not today_rows:
        print(f"sync_applications: no rows for {TODAY} — nothing to sync")
        return

    applications = [
        {
            "date_applied": r.get("date_applied", TODAY),
            "company": r.get("company", ""),
            "role": r.get("role", ""),
            "url": r.get("url", ""),
            # Automation default is Found — the /ingest endpoint additionally
            # coerces any non-automation status; only the user sets Applied.
            "status": r.get("status", "Found"),
            "notes": r.get("notes", ""),
        }
        for r in today_rows
        if r.get("company")
    ]

    payload = {"secret": INGEST_SECRET, "applications": applications}
    resp = requests.post(f"{API_URL}/ingest/applications", json=payload, timeout=15)
    if resp.ok:
        data = resp.json()
        print(f"sync_applications: upserted {data.get('upserted', 0)} application(s) for {TODAY}")
    else:
        print(f"sync_applications: ERROR {resp.status_code} — {resp.text[:200]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
