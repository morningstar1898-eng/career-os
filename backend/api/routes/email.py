import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from api.db import get_db

router = APIRouter()


class BriefingEmailRequest(BaseModel):
    secret: str
    to: str


@router.post("/briefing")
def send_briefing_email(req: BriefingEmailRequest):
    expected = os.getenv("INGEST_SECRET", "")
    if not expected or req.secret != expected:
        raise HTTPException(403, "Invalid secret")

    today = datetime.utcnow().strftime("%Y-%m-%d")

    with get_db() as conn:
        row = conn.execute(
            "SELECT content_json FROM briefings WHERE date = ?", (today,)
        ).fetchone()

    if not row:
        raise HTTPException(404, "No briefing found for today")

    import json
    content = json.loads(row["content_json"])
    raw = content.get("raw_output", "No content available.")

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #111; color: #e4e4e7;">
  <div style="border-bottom: 2px solid #a78bfa; padding-bottom: 12px; margin-bottom: 20px;">
    <h1 style="margin: 0; font-size: 22px; color: #a78bfa;">Career OS Daily Briefing</h1>
    <p style="margin: 4px 0 0; font-size: 13px; color: #71717a;">{today}</p>
  </div>
  <div style="background: #1a1a2e; border-radius: 8px; padding: 16px; white-space: pre-wrap; line-height: 1.6; font-size: 14px; color: #d4d4d8;">
{raw}
  </div>
  <p style="margin-top: 20px; font-size: 11px; color: #52525b; text-align: center;">
    Sent automatically by Career OS
  </p>
</body>
</html>"""

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_pass:
        raise HTTPException(500, "SMTP credentials not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Career OS Briefing — {today}"
    msg["From"] = smtp_user
    msg["To"] = req.to
    msg.attach(MIMEText(raw, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [req.to], msg.as_string())
    except Exception as e:
        raise HTTPException(500, f"Failed to send email: {str(e)[:200]}")

    return {"status": "ok", "to": req.to, "date": today}
