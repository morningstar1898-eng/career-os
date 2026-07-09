"""
auto_submit/reviewer.py
The second-agent correctness gate. A SEPARATE model call (Sonnet — stronger
than the Haiku drafter) reviews each application package against the LIVE
posting page before anything is submitted.

Fail-closed by design: any API error, malformed response, or uncertainty
→ REJECT, and the job falls back to "Ready to Apply" for manual handling.
The reviewer also returns the exact cover-letter text to submit, extracted
from the drafter's mixed materials blob (cover letter + resume bullets +
ATS notes) — so the form never receives the raw internal notes.
"""
import json
import os
import re

REVIEWER_MODEL = os.getenv(
    "REVIEWER_MODEL", "anthropic/claude-sonnet-4-5-20250929"
)

# Placeholder artifacts that must never reach an employer.
PLACEHOLDER_PATTERN = re.compile(
    r"\[(?:team|role|company|name|manager|title|date|X{1,3}|insert[^\]]*)\]"
    r"|\bTBD\b|\bTODO\b|\{\{[^}]*\}\}|lorem ipsum",
    re.IGNORECASE,
)

SYSTEM_PROMPT = """You are the final reviewer in a job-application pipeline. \
A drafting agent wrote application materials; your job is to decide whether they are \
correct and safe to submit to a REAL employer on the candidate's behalf. You are the \
last line of defense — when in doubt, REJECT. A rejected application simply goes back \
to the candidate for manual review; a bad approved one goes to an employer under her name.

Check ALL of the following:
1. POSTING MATCH — the live posting page text provided must actually be for the stated \
company and a role matching the stated title (minor title variations are fine; a \
different company or clearly different role is a REJECT).
2. MATERIALS CORRECTNESS — the cover letter names the RIGHT company and role, contains \
no leftover placeholders (e.g. "[team]", "[role]", "TBD"), no meta-commentary from the \
drafting agent, and reads as a finished professional letter.
3. TRUTHFULNESS — every claim in the cover letter is supported by the resume provided. \
Reject anything that fabricates experience, employers, titles, or credentials.
4. EXTRACTION — from the raw materials, extract ONLY the final cover letter text \
(no resume bullets, no 'ATS Match' lines, no headers like 'COVER LETTER:').

Respond with ONLY a JSON object, no markdown fences:
{"verdict": "APPROVE" or "REJECT",
 "reasons": ["short reason", ...],
 "cover_letter": "exact final cover letter text to submit (empty string if REJECT)"}"""


def review_application(job: dict, page_text: str, materials: str, resume_text: str) -> dict:
    """Returns {"verdict": "APPROVE"|"REJECT", "reasons": [...], "cover_letter": str}."""
    user_msg = (
        f"CANDIDATE RESUME:\n{resume_text[:5000]}\n\n"
        f"TARGET JOB: {job.get('company')} — {job.get('role')}\n"
        f"POSTING URL: {job.get('url')}\n\n"
        f"LIVE POSTING PAGE TEXT (fetched just now):\n{page_text[:6000]}\n\n"
        f"DRAFTED MATERIALS (raw, from the drafting agent):\n{materials[:6000]}"
    )
    try:
        # Imported lazily so the pure parsing/gating logic (and its tests)
        # never needs the LLM stack installed.
        from litellm import completion

        resp = completion(
            model=REVIEWER_MODEL,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=2000,
            temperature=0.0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or ""
        verdict = _parse_verdict(raw)
    except Exception as e:
        return _reject(f"reviewer call failed: {type(e).__name__}: {str(e)[:150]}")

    if verdict["verdict"] != "APPROVE":
        verdict["verdict"] = "REJECT"
        return verdict

    # Belt-and-braces: even on APPROVE, hard-fail placeholders and empty letters.
    letter = verdict.get("cover_letter", "").strip()
    if len(letter) < 200:
        return _reject("approved cover letter is implausibly short")
    if PLACEHOLDER_PATTERN.search(letter):
        return _reject("cover letter contains unfilled placeholders")
    company = (job.get("company") or "").split("/")[0].split("(")[0].strip()
    if company and company.lower() not in letter.lower():
        return _reject(f"cover letter never names the company '{company}'")

    verdict["cover_letter"] = letter
    return verdict


def _parse_verdict(raw: str) -> dict:
    """Extract the JSON object from the model reply. Fail-closed."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.S)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        return _reject("reviewer returned no JSON")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return _reject("reviewer returned malformed JSON")
    if not isinstance(data, dict) or data.get("verdict") not in ("APPROVE", "REJECT"):
        return _reject("reviewer returned no valid verdict")
    data.setdefault("reasons", [])
    data.setdefault("cover_letter", "")
    return data


def _reject(reason: str) -> dict:
    return {"verdict": "REJECT", "reasons": [reason], "cover_letter": ""}
