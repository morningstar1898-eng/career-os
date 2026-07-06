"""
api/config.py
Central backend configuration. Every setting is read from the environment at
call time (not import time) so tests and redeploys pick up changes without
re-importing modules.

Required in production:
    CAREER_OS_API_TOKEN   — bearer token protecting all private routes
Optional:
    CAREER_OS_DB          — SQLite path (default: backend/career_os.db)
    CAREER_OS_DEMO_DB     — SQLite path used when PUBLIC_DEMO_MODE=true
    ENV                   — "production" disables demo routes
    PUBLIC_DEMO_MODE      — "true" serves ONLY the sanitized demo database
    ALLOW_MANUAL_RUNS     — "true" enables POST /runs/trigger
    ALLOWED_ORIGINS       — comma-separated CORS origins (falls back to
                            legacy CORS_ORIGINS, then localhost:3000)
    GOOGLE_SHEET_URL      — tracker link rendered in the briefing email footer
"""
import os


def _flag(name: str, default: str = "") -> bool:
    return os.getenv(name, default).lower() == "true"


def env_name() -> str:
    return os.getenv("ENV", "development").lower()


# ── Branding ──────────────────────────────────────────────
def app_name() -> str:
    """Internal name (repo/infra compatibility)."""
    return os.getenv("APP_NAME", "CareerOS")


def public_app_name() -> str:
    """User-facing display name — configurable so the SaaS brand can change."""
    return os.getenv("PUBLIC_APP_NAME", "Career OS")


# ── Multi-user auth (SaaS) ────────────────────────────────
def auth_secret() -> str:
    """HMAC secret for user session JWTs. Required for SaaS routes."""
    return os.getenv("AUTH_SECRET", "")


def admin_email() -> str:
    """Signups matching this email are bootstrapped with the admin role."""
    return os.getenv("ADMIN_EMAIL", "").strip().lower()


# ── Trial / billing ───────────────────────────────────────
def trial_days() -> int:
    try:
        return int(os.getenv("TRIAL_DAYS", "3"))
    except ValueError:
        return 3


def stripe_secret_key() -> str:
    return os.getenv("STRIPE_SECRET_KEY", "")


def stripe_webhook_secret() -> str:
    return os.getenv("STRIPE_WEBHOOK_SECRET", "")


def stripe_price_to_plan() -> dict:
    """Map Stripe price IDs (from env) to internal plan names."""
    return {
        os.getenv("STRIPE_PRICE_STARTER", ""): "starter",
        os.getenv("STRIPE_PRICE_PRO", ""): "pro",
        os.getenv("STRIPE_PRICE_PREMIUM", ""): "premium",
    }


# ── Gmail integration ─────────────────────────────────────
def gmail_client_id() -> str:
    return os.getenv("GMAIL_CLIENT_ID", "")


def gmail_client_secret() -> str:
    return os.getenv("GMAIL_CLIENT_SECRET", "")


def gmail_redirect_uri() -> str:
    return os.getenv("GMAIL_REDIRECT_URI", "")


def gmail_configured() -> bool:
    return bool(gmail_client_id() and gmail_client_secret() and gmail_redirect_uri())


# ── Kill switches (admin cost/abuse protection) ───────────
def disable_ai_runs() -> bool:
    return _flag("DISABLE_AI_RUNS")


def disable_gmail_sync() -> bool:
    return _flag("DISABLE_GMAIL_SYNC")


def disable_application_assist() -> bool:
    return _flag("DISABLE_APPLICATION_ASSIST")


def disable_new_signups() -> bool:
    return _flag("DISABLE_NEW_SIGNUPS")


# ── Database (SaaS migration path) ────────────────────────
def database_url() -> str:
    """When set (e.g. postgresql://...), signals the Postgres migration path.
    The current implementation runs on SQLite; see docs/SAAS_MIGRATION.md."""
    return os.getenv("DATABASE_URL", "")


def is_production() -> bool:
    return env_name() == "production"


def api_token() -> str:
    return os.getenv("CAREER_OS_API_TOKEN", "")


def allow_manual_runs() -> bool:
    return os.getenv("ALLOW_MANUAL_RUNS", "").lower() == "true"


def public_demo_mode() -> bool:
    return os.getenv("PUBLIC_DEMO_MODE", "").lower() == "true"


def demo_routes_enabled() -> bool:
    """Demo seeding is available outside production, or in explicit demo mode."""
    return (not is_production()) or public_demo_mode()


def db_path() -> str:
    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    if public_demo_mode():
        # Demo mode NEVER touches the real database — sanitized sample data only.
        return os.getenv("CAREER_OS_DEMO_DB", os.path.join(backend_dir, "career_os_demo.db"))
    return os.getenv("CAREER_OS_DB", os.path.join(backend_dir, "career_os.db"))


def allowed_origins() -> list[str]:
    raw = os.getenv("ALLOWED_ORIGINS") or os.getenv("CORS_ORIGINS") or "http://localhost:3000"
    return [o.strip() for o in raw.split(",") if o.strip()]


def google_sheet_url() -> str:
    return os.getenv("GOOGLE_SHEET_URL", "")
