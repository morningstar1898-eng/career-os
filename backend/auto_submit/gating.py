"""
auto_submit/gating.py
Pure decision logic for whether a job may be auto-submitted. No network, no
side effects — fully unit-testable. Every rule here is a safety guarantee:

  1. APPLY_MODE must be 'auto' (repo variable — the user's explicit choice).
  2. Optum/UHG internal roles are NEVER auto-submitted. The candidate is a
     current employee; internal transfers always get human eyes.
  3. Only supported ATSs (validated separately via ats.validate_posting).
  4. Never submit twice to the same company+role (any prior Submitted/Applied
     row in the tracker blocks a resubmit).
  5. Daily cap (MAX_AUTO_SUBMITS_PER_DAY, default 5).
  6. Materials must exist — no materials, no submission.
"""
from dataclasses import dataclass, field

# Company names that always mean "internal transfer — manual only".
INTERNAL_EMPLOYERS = ("optum", "unitedhealth", "uhg", "united health")

# Sheet statuses that count as "already sent" for dedupe purposes.
ALREADY_SENT_STATUSES = (
    "submitted (auto)", "applied", "confirmation received", "recruiter screen",
    "assessment", "phone screen", "interview", "offer",
)


@dataclass
class GateDecision:
    action: str          # "auto" | "manual" | "skip"
    reason: str = "ok"


@dataclass
class GateContext:
    apply_mode: str = "review"
    max_per_day: int = 5
    submitted_today: int = 0
    # (company_lower, role_lower) pairs already sent per the tracker sheet
    already_sent: set = field(default_factory=set)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def is_internal(company: str, notes: str = "") -> bool:
    text = f"{_norm(company)} {_norm(notes)}"
    return any(e in text for e in INTERNAL_EMPLOYERS) or "internal" in _norm(notes)


def decide(job: dict, ctx: GateContext, has_materials: bool) -> GateDecision:
    """job needs keys: company, role, url, notes (all strings)."""
    if ctx.apply_mode != "auto":
        return GateDecision("manual", "APPLY_MODE is not 'auto'")

    if is_internal(job.get("company", ""), job.get("notes", "")):
        return GateDecision(
            "manual",
            "Optum/UHG internal transfer — always applied manually (policy)",
        )

    key = (_norm(job.get("company")), _norm(job.get("role")))
    if key in ctx.already_sent:
        return GateDecision("skip", "already submitted/applied to this company+role")

    if not job.get("url", "").strip().startswith("http"):
        return GateDecision("manual", "no usable posting URL")

    if not has_materials:
        return GateDecision("manual", "no drafted materials found for this role")

    if ctx.submitted_today >= ctx.max_per_day:
        return GateDecision("manual", f"daily auto-submit cap reached ({ctx.max_per_day})")

    return GateDecision("auto")
