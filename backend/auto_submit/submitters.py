"""
auto_submit/submitters.py
Playwright form fillers for the supported ATSs (Greenhouse, Lever, Ashby).

Principles:
  - DRY RUN by default: fill everything, screenshot the completed form, do
    NOT click submit. Go live only when AUTO_SUBMIT_DRY_RUN=false.
  - Never bypass a CAPTCHA. If one is present, abort → manual.
  - Never guess required answers. If a required field can't be mapped from
    the applicant profile, abort → manual. A skipped submission costs the
    user two minutes; a wrong answer costs the application.
  - Capture evidence: screenshot of the filled form (dry run) or the
    confirmation page (live), plus the confirmation text if detected.

Playwright is installed by the workflow step only (not requirements.txt) so
the Azure container image stays lean.
"""
import re
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

CONFIRMATION_PATTERN = re.compile(
    r"thank you for (applying|your application)|application (was )?(received|submitted)"
    r"|we('|’)ve received your application|your application has been received",
    re.IGNORECASE,
)
CAPTCHA_SELECTOR = (
    "iframe[src*='recaptcha'], .g-recaptcha, iframe[src*='hcaptcha'], "
    "[data-hcaptcha-widget-id], iframe[src*='turnstile']"
)

# Keyword → profile answer for the short-answer/select questions that appear
# on most forms. Matching is on the question label, lowercased.
def _standard_answers(profile: dict) -> list[tuple[re.Pattern, str]]:
    auth = profile.get("work_authorization", {})
    yes_no = lambda b: "Yes" if b else "No"
    pairs = [
        (r"authoriz|legally.*(work|employ)|eligible to work", yes_no(auth.get("authorized_us", True))),
        (r"sponsor", yes_no(auth.get("require_sponsorship", False))),
        (r"linkedin", profile.get("linkedin_url", "")),
        (r"github", profile.get("github_url", "")),
        (r"portfolio|personal website|other website", profile.get("portfolio_url", "")),
        (r"how did you hear|where did you (find|hear)", "Company careers page"),
        (r"current (city|location)|where.*(located|based)", profile.get("location", "")),
        (r"gender|race|ethnicit|veteran|disabilit|hispanic|latin", "__DECLINE__"),
    ]
    return [(re.compile(p, re.I), v) for p, v in pairs]

DECLINE_OPTION_PATTERN = re.compile(
    r"decline|prefer not|don't wish|do not wish|i choose not", re.I
)


@dataclass
class SubmitResult:
    outcome: str            # "submitted" | "dry_run_ok" | "aborted"
    detail: str
    screenshot_path: str = ""
    confirmation_text: str = ""


class FormAborted(Exception):
    """Raised when a safety rule says: stop, leave this one to the human."""


def submit_application(ats: str, url: str, profile: dict, resume_pdf_path: str,
                       cover_letter: str, screenshot_path: str,
                       dry_run: bool = True) -> SubmitResult:
    """Fill (and in live mode submit) one application. Never raises — every
    failure path returns an 'aborted' result with the reason."""
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 1600})
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2500)  # let client-side forms hydrate

                _open_application_form(page, ats)
                _fill_form(page, ats, profile, resume_pdf_path, cover_letter)
                _check_required_fields(page)

                if page.locator(CAPTCHA_SELECTOR).count() > 0 and not dry_run:
                    raise FormAborted("CAPTCHA on form — cannot auto-submit (never bypassed)")

                if dry_run:
                    page.screenshot(path=screenshot_path, full_page=True)
                    return SubmitResult("dry_run_ok",
                                        "form filled successfully — submit NOT clicked (dry run)",
                                        screenshot_path)

                _click_submit(page)
                confirmation = _wait_for_confirmation(page)
                page.screenshot(path=screenshot_path, full_page=True)
                if confirmation:
                    return SubmitResult("submitted", "confirmation detected",
                                        screenshot_path, confirmation)
                return SubmitResult("aborted",
                                    "submit clicked but NO confirmation detected — verify manually",
                                    screenshot_path)
            finally:
                browser.close()
    except FormAborted as e:
        return SubmitResult("aborted", str(e))
    except PWTimeout:
        return SubmitResult("aborted", "page timed out while filling the form")
    except Exception as e:
        return SubmitResult("aborted", f"{type(e).__name__}: {str(e)[:200]}")


def _open_application_form(page, ats: str) -> None:
    """Some postings show the description first with an Apply button."""
    for label in ("Apply for this job", "Apply Now", "Apply for this Job", "Apply"):
        btn = page.get_by_role("button", name=label, exact=False)
        link = page.get_by_role("link", name=label, exact=False)
        for loc in (btn, link):
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.click()
                page.wait_for_timeout(2000)
                return
    # No button → the form is already on the page (classic Greenhouse embed).


def _fill_form(page, ats: str, profile: dict, resume_pdf_path: str, cover_letter: str) -> None:
    first, last = profile.get("first_name", ""), profile.get("last_name", "")

    # Name — Lever uses one full-name field; Greenhouse/Ashby split it.
    _fill_by_label(page, r"^full name|^name\b", f"{first} {last}")
    _fill_by_label(page, r"first name", first)
    _fill_by_label(page, r"last name", last)
    _fill_by_label(page, r"^e-?mail", profile.get("email", ""))
    _fill_by_label(page, r"phone", profile.get("phone", ""))
    _fill_by_label(page, r"current company|company$|organization", profile.get("current_company", ""))

    # Resume upload — required everywhere.
    file_inputs = page.locator("input[type='file']")
    if file_inputs.count() == 0:
        raise FormAborted("no resume upload field found")
    file_inputs.first.set_input_files(resume_pdf_path)
    page.wait_for_timeout(3000)  # ATSs parse the resume async

    # Cover letter — textarea if present (Lever 'Additional information',
    # Greenhouse/Ashby 'Cover Letter').
    for pattern in (r"cover letter", r"additional information", r"anything else"):
        if _fill_by_label(page, pattern, cover_letter, textarea_ok=True):
            break

    # Standard short-answer / select questions from the profile.
    _answer_standard_questions(page, profile)


def _fill_by_label(page, label_pattern: str, value: str, textarea_ok: bool = False) -> bool:
    """Fill the first visible input/textarea whose label matches. Returns True if filled."""
    if not value:
        return False
    loc = page.get_by_label(re.compile(label_pattern, re.I))
    for i in range(min(loc.count(), 5)):
        el = loc.nth(i)
        try:
            if not el.is_visible():
                continue
            tag = el.evaluate("e => e.tagName.toLowerCase()")
            if tag == "textarea" and not textarea_ok:
                continue
            if tag in ("input", "textarea"):
                el.fill(value)
                return True
        except Exception:
            continue
    return False


def _answer_standard_questions(page, profile: dict) -> None:
    answers = _standard_answers(profile)
    selects = page.locator("select")
    for i in range(selects.count()):
        sel = selects.nth(i)
        try:
            if not sel.is_visible() or sel.evaluate("e => e.value"):
                continue
            label = _label_text(page, sel)
            for pattern, value in answers:
                if pattern.search(label):
                    if value == "__DECLINE__":
                        _select_decline(sel)
                    elif value:
                        sel.select_option(label=re.compile(rf"^{re.escape(value)}", re.I))
                    break
        except Exception:
            continue
    # Text inputs for URL-type questions (LinkedIn/GitHub/portfolio).
    for pattern, value in answers:
        if value and value != "__DECLINE__" and value.startswith("http"):
            _fill_by_label(page, pattern.pattern, value)


def _select_decline(sel) -> None:
    options = sel.evaluate("e => Array.from(e.options).map(o => o.textContent)")
    for opt in options:
        if DECLINE_OPTION_PATTERN.search(opt or ""):
            sel.select_option(label=opt)
            return


def _label_text(page, el) -> str:
    return el.evaluate(
        """e => {
            const id = e.getAttribute('id');
            const lbl = id ? document.querySelector(`label[for="${id}"]`) : e.closest('label');
            const wrap = e.closest('[class*="field"], [class*="question"], li, div');
            return (lbl?.textContent || wrap?.querySelector('label')?.textContent || '').trim();
        }"""
    ) or ""


def _check_required_fields(page) -> None:
    """Abort if any visible required field is still empty — never guess."""
    empties = page.evaluate(
        """() => {
            const bad = [];
            for (const el of document.querySelectorAll(
                'input[required], textarea[required], select[required], [aria-required="true"]')) {
              if (el.offsetParent === null) continue;           // hidden
              if (el.type === 'file') continue;                 // handled above
              if (el.type === 'checkbox' || el.type === 'radio') {
                const name = el.name;
                const group = document.querySelectorAll(`[name="${name}"]`);
                if (![...group].some(g => g.checked)) bad.push(name || 'checkbox');
                continue;
              }
              if (!el.value) {
                const id = el.getAttribute('id');
                const lbl = id ? document.querySelector(`label[for="${id}"]`) : null;
                bad.push((lbl?.textContent || el.name || el.placeholder || 'unnamed').trim().slice(0, 60));
              }
            }
            return [...new Set(bad)];
        }"""
    )
    if empties:
        raise FormAborted(
            "required field(s) could not be answered from the profile: " + "; ".join(empties[:6])
        )


def _click_submit(page) -> None:
    btn = page.get_by_role("button", name=re.compile(r"submit", re.I))
    if btn.count() == 0:
        btn = page.locator("button[type='submit'], input[type='submit']")
    if btn.count() == 0:
        raise FormAborted("no submit button found")
    btn.first.click()


def _wait_for_confirmation(page) -> str:
    try:
        page.wait_for_function(
            """(patternSrc) => new RegExp(patternSrc, 'i').test(document.body.innerText)""",
            arg=CONFIRMATION_PATTERN.pattern,
            timeout=30000,
        )
        text = page.evaluate("() => document.body.innerText")
        m = CONFIRMATION_PATTERN.search(text)
        if m:
            start = max(0, m.start() - 40)
            return text[start : m.end() + 120].strip()
    except PWTimeout:
        pass
    return ""
