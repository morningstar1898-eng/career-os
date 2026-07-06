import html as html_lib
import os
import re
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


# ── Markdown → HTML renderer ─────────────────────────────────────────────────

_SECTION_COLORS = {
    "market signal":   ("#7c3aed", "#1e1b4b"),  # purple — skill gaps
    "lesson":          ("#0369a1", "#0c1a2e"),  # blue   — learning
    "jobs applied":    ("#065f46", "#052e1c"),  # green  — applications
    "project":         ("#92400e", "#1c0e05"),  # amber  — portfolio
    "interview prep":  ("#be185d", "#1f0a14"),  # pink   — Q&A
    "tomorrow":        ("#374151", "#111827"),  # gray   — preview
}

def _section_color(title_lower: str):
    for key, colors in _SECTION_COLORS.items():
        if key in title_lower:
            return colors
    return ("#4b5563", "#111827")


def _inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) to HTML.

    The input is AI/web-derived text — escape it FIRST so it can never inject
    raw HTML into the email, then apply the markdown formatting.
    """
    text = html_lib.escape(text, quote=False)
    # Bold+italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Inline code
    text = re.sub(r"`([^`]+)`", r'<code style="background:#1e293b;color:#7dd3fc;padding:1px 5px;border-radius:3px;font-size:12px;font-family:monospace;">\1</code>', text)
    return text


def _render_table(lines: list[str]) -> str:
    """Render a markdown table as HTML."""
    rows = []
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if i == 0:
            cells_html = "".join(
                f'<th style="padding:8px 12px;text-align:left;border-bottom:1px solid #374151;color:#a78bfa;font-size:12px;text-transform:uppercase;letter-spacing:.05em;">{c}</th>'
                for c in cells
            )
            rows.append(f"<thead><tr>{cells_html}</tr></thead><tbody>")
        elif re.match(r"^[\s|:\-]+$", line):
            continue  # separator row
        else:
            cells_html = "".join(
                f'<td style="padding:8px 12px;border-bottom:1px solid #1f2937;color:#d1d5db;font-size:13px;">{_inline(c)}</td>'
                for c in cells
            )
            rows.append(f"<tr>{cells_html}</tr>")
    if rows:
        rows.append("</tbody>")
    return (
        '<div style="overflow-x:auto;margin:12px 0;">'
        '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
        + "".join(rows)
        + "</table></div>"
    )


def _render_code_block(code: str, lang: str = "") -> str:
    escaped = code.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lang_label = f'<span style="color:#6b7280;font-size:10px;text-transform:uppercase;letter-spacing:.1em;">{lang}</span>' if lang else ""
    return (
        f'<div style="background:#0f172a;border:1px solid #1e293b;border-radius:8px;margin:12px 0;overflow:hidden;">'
        f'<div style="background:#1e293b;padding:6px 14px;display:flex;justify-content:space-between;align-items:center;">'
        f'<span style="color:#94a3b8;font-size:11px;">code</span>{lang_label}</div>'
        f'<pre style="margin:0;padding:16px;overflow-x:auto;font-family:\'Menlo\',\'Consolas\',monospace;font-size:12px;line-height:1.7;color:#e2e8f0;">{escaped}</pre>'
        f'</div>'
    )


def _render_section(title: str, body_lines: list[str]) -> str:
    """Render a ## section with color-coded header and parsed body."""
    accent, bg = _section_color(title.lower())

    body_html = _render_body(body_lines)

    return (
        f'<div style="margin-bottom:24px;border-radius:10px;overflow:hidden;border:1px solid {accent}33;">'
        f'<div style="background:{accent};padding:10px 16px;">'
        f'<h2 style="margin:0;font-size:15px;font-weight:700;color:#fff;letter-spacing:.01em;">{_inline(title)}</h2>'
        f'</div>'
        f'<div style="background:{bg};padding:16px;">{body_html}</div>'
        f'</div>'
    )


def _render_body(lines: list[str]) -> str:
    """Convert body lines (already split) to HTML, handling code blocks, tables, lists."""
    html_parts = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # ── Fenced code block ──────────────────────────────
        fence_match = re.match(r"^```(\w*)\s*$", line)
        if fence_match:
            lang = fence_match.group(1)
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code_lines.append(lines[i])
                i += 1
            html_parts.append(_render_code_block("\n".join(code_lines), lang))
            i += 1
            continue

        # ── Table ──────────────────────────────────────────
        if "|" in line and re.match(r"^\|?[^|]+\|", line):
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            html_parts.append(_render_table(table_lines))
            continue

        # ── H3 subheading ──────────────────────────────────
        if line.startswith("### "):
            text = line[4:].strip()
            html_parts.append(
                f'<h3 style="margin:18px 0 6px;font-size:13px;font-weight:700;color:#c4b5fd;'
                f'text-transform:uppercase;letter-spacing:.06em;">{_inline(text)}</h3>'
            )
            i += 1
            continue

        # ── H4 subheading ──────────────────────────────────
        if line.startswith("#### "):
            text = line[5:].strip()
            html_parts.append(
                f'<h4 style="margin:14px 0 4px;font-size:13px;font-weight:600;color:#93c5fd;">{_inline(text)}</h4>'
            )
            i += 1
            continue

        # ── Numbered list ──────────────────────────────────
        if re.match(r"^\d+\.", line):
            items = []
            while i < len(lines) and re.match(r"^\d+\.\s", lines[i]):
                items.append(f'<li style="margin:4px 0;color:#d1d5db;font-size:13px;line-height:1.6;">{_inline(lines[i].split(".", 1)[1].strip())}</li>')
                i += 1
            html_parts.append(f'<ol style="margin:8px 0;padding-left:20px;">{"".join(items)}</ol>')
            continue

        # ── Bullet list ────────────────────────────────────
        if line.startswith("- ") or line.startswith("* "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or lines[i].startswith("* ")):
                items.append(f'<li style="margin:4px 0;color:#d1d5db;font-size:13px;line-height:1.6;">{_inline(lines[i][2:])}</li>')
                i += 1
            html_parts.append(f'<ul style="margin:8px 0;padding-left:20px;">{"".join(items)}</ul>')
            continue

        # ── Blockquote / callout ────────────────────────────
        if line.startswith("> "):
            text = line[2:]
            html_parts.append(
                f'<blockquote style="margin:10px 0;padding:10px 14px;border-left:3px solid #7c3aed;'
                f'background:#1e1b4b;border-radius:0 6px 6px 0;color:#c4b5fd;font-size:13px;'
                f'font-style:italic;">{_inline(text)}</blockquote>'
            )
            i += 1
            continue

        # ── Horizontal rule ────────────────────────────────
        if re.match(r"^---+$", line.strip()):
            html_parts.append('<hr style="border:none;border-top:1px solid #1f2937;margin:16px 0;">')
            i += 1
            continue

        # ── Empty line ─────────────────────────────────────
        if not line.strip():
            i += 1
            continue

        # ── Normal paragraph ───────────────────────────────
        html_parts.append(
            f'<p style="margin:6px 0;color:#d1d5db;font-size:13px;line-height:1.7;">{_inline(line)}</p>'
        )
        i += 1

    return "\n".join(html_parts)


def briefing_to_html(raw: str, date: str) -> str:
    """Convert raw markdown briefing to a structured HTML email."""
    lines = raw.split("\n")

    # Split into top-level ## sections
    sections: list[tuple[str, list[str]]] = []
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("# "):
            # Top-level title — skip (rendered in header)
            continue
        if line.startswith("## "):
            if current_lines or current_title:
                sections.append((current_title, current_lines))
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title or current_lines:
        sections.append((current_title, current_lines))

    # Render each section
    sections_html = ""
    for title, body_lines in sections:
        if not title and not any(l.strip() for l in body_lines):
            continue
        sections_html += _render_section(title, body_lines)

    formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%A, %B %d %Y")

    # Tracker link comes from env — no private URLs hardcoded in source.
    sheet_url = os.getenv("GOOGLE_SHEET_URL", "")
    tracker_link = (
        f'&nbsp;&middot;&nbsp;<a href="{html_lib.escape(sheet_url, quote=True)}" '
        f'style="color:#6366f1;text-decoration:none;">Application Tracker</a>'
    ) if sheet_url else ""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Career OS — {formatted_date}</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0f;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:640px;margin:0 auto;padding:24px 16px;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#1e1b4b 0%,#0f172a 100%);border-radius:12px;padding:24px;margin-bottom:24px;border:1px solid #3730a3;">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">
        <div style="width:8px;height:8px;background:#a78bfa;border-radius:50%;"></div>
        <span style="font-size:11px;color:#6366f1;font-weight:600;text-transform:uppercase;letter-spacing:.1em;">Career OS</span>
      </div>
      <h1 style="margin:0 0 4px;font-size:22px;font-weight:800;color:#f9fafb;">Daily Briefing</h1>
      <p style="margin:0;font-size:13px;color:#6b7280;">{formatted_date}</p>
    </div>

    <!-- Sections -->
    {sections_html}

    <!-- Footer -->
    <div style="margin-top:32px;padding-top:16px;border-top:1px solid #1f2937;text-align:center;">
      <p style="margin:0;font-size:11px;color:#4b5563;">
        Generated by Career OS{tracker_link}
      </p>
    </div>

  </div>
</body>
</html>"""


# ── Email endpoint ────────────────────────────────────────────────────────────

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

    html = briefing_to_html(raw, today)

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASSWORD", "")

    if not smtp_user or not smtp_pass:
        raise HTTPException(500, "SMTP credentials not configured")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Career OS — {datetime.utcnow().strftime('%a %b %d')} · Daily Briefing"
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
