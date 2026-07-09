"""
auto_submit/ats.py
Detect which ATS a posting URL belongs to and verify the posting is real.

Only ATSs with public, no-login application forms are supported. Workday,
LinkedIn, Indeed, and company portals that require an account can NOT be
auto-submitted (and we never try) — those jobs stay manual.
"""
import re
import requests

# ATS id → URL patterns that identify a canonical application page.
SUPPORTED_ATS = {
    "greenhouse": [
        r"boards\.greenhouse\.io/[^/]+/jobs/\d+",
        r"job-boards\.greenhouse\.io/[^/]+/jobs/\d+",
    ],
    "lever": [
        r"jobs\.lever\.co/[^/]+/[0-9a-f-]{36}",
    ],
    "ashby": [
        r"jobs\.ashbyhq\.com/[^/]+/[0-9a-f-]{36}",
    ],
}

# Markers on a fetched page that mean the posting is gone/closed.
DEAD_POSTING_MARKERS = [
    "job you are looking for is no longer open",
    "this job is no longer available",
    "position has been filled",
    "job not found",
    "posting not found",
    "no longer accepting applications",
]

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}


def detect_ats(url: str) -> str | None:
    """Return the ATS id for a URL, or None if unsupported. Pure — no network."""
    if not url:
        return None
    for ats, patterns in SUPPORTED_ATS.items():
        for pat in patterns:
            if re.search(pat, url):
                return ats
    return None


def validate_posting(url: str, timeout: int = 20) -> dict:
    """Fetch the posting URL (following redirects) and confirm it is a live
    posting on a supported ATS. Aggregator links sometimes redirect to the
    real ATS page, so the ATS is detected on the FINAL url.

    Returns {ok, ats, final_url, page_text, reason}. Fail-closed: any
    network error or dead-posting marker → ok=False.
    """
    result = {"ok": False, "ats": None, "final_url": url, "page_text": "", "reason": ""}
    try:
        resp = requests.get(url, headers=_UA, timeout=timeout, allow_redirects=True)
    except requests.RequestException as e:
        result["reason"] = f"URL unreachable: {type(e).__name__}"
        return result

    result["final_url"] = resp.url
    if resp.status_code != 200:
        result["reason"] = f"HTTP {resp.status_code}"
        return result

    ats = detect_ats(resp.url) or detect_ats(url)
    if not ats:
        result["reason"] = "not a supported ATS (Greenhouse/Lever/Ashby) — manual apply"
        return result

    text = _strip_html(resp.text)
    lowered = text.lower()
    for marker in DEAD_POSTING_MARKERS:
        if marker in lowered:
            result["reason"] = f"posting appears closed ('{marker}')"
            return result

    result.update(ok=True, ats=ats, page_text=text[:8000], reason="ok")
    return result


def _strip_html(html: str) -> str:
    """Crude but dependency-free HTML → text for the reviewer's context."""
    html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;|&amp;|&#\d+;|&[a-z]+;", " ", html)
    return re.sub(r"\s+", " ", html).strip()
