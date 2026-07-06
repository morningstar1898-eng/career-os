import logging
import sys
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api import config
from api.db import init_db
from api.deps import require_api_token
from api.routes.runs import router as runs_router
from api.routes.briefings import router as briefings_router
from api.routes.analytics import router as analytics_router
from api.routes.interview import router as interview_router
from api.routes.demo import router as demo_router
from api.routes.tts import router as tts_router
from api.routes.auth import router as auth_router
from api.routes.ingest import router as ingest_router
from api.routes.activity import router as activity_router
from api.routes.email import router as email_router
from api.routes.pipeline import router as pipeline_router
from api.ws import router as ws_router

# Multi-user SaaS routers (per-user JWT auth handled inside each route)
from api.saas.routes.auth import router as saas_auth_router
from api.saas.routes.profile import router as saas_profile_router
from api.saas.routes.jobs import router as saas_jobs_router
from api.saas.routes.growth import router as saas_growth_router
from api.saas.routes.gmail import router as saas_gmail_router
from api.saas.routes.billing import router as saas_billing_router
from api.saas.routes.assist import router as saas_assist_router
from api.saas.routes.admin import router as saas_admin_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("career_os")

app = FastAPI(title=f"{config.public_app_name()} API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Every private router requires a bearer token (CAREER_OS_API_TOKEN or a
# session token from /auth/login). Only /health and /auth/* are public.
PRIVATE = [Depends(require_api_token)]

app.include_router(runs_router, prefix="/runs", tags=["runs"], dependencies=PRIVATE)
app.include_router(briefings_router, prefix="/briefings", tags=["briefings"], dependencies=PRIVATE)
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"], dependencies=PRIVATE)
app.include_router(interview_router, prefix="/interview", tags=["interview"], dependencies=PRIVATE)
app.include_router(tts_router, prefix="/tts", tags=["tts"], dependencies=PRIVATE)
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"], dependencies=PRIVATE)
app.include_router(activity_router, prefix="/activity", tags=["activity"], dependencies=PRIVATE)
app.include_router(email_router, prefix="/email", tags=["email"], dependencies=PRIVATE)
app.include_router(pipeline_router, prefix="/pipeline", tags=["pipeline"], dependencies=PRIVATE)
app.include_router(ws_router, tags=["websocket"])

# Demo seeding is never registered in production (unless PUBLIC_DEMO_MODE,
# which serves a separate sanitized database). Still requires auth.
if config.demo_routes_enabled():
    app.include_router(demo_router, prefix="/demo", tags=["demo"], dependencies=PRIVATE)

# ── Multi-user SaaS API (v1) ──────────────────────────────
# Per-user JWT auth is enforced by get_current_user/require_admin inside each
# route (they need the user row, not just a static token). Signup/login and
# the plan catalog are the public entry points; the Stripe webhook
# authenticates via its HMAC signature.
for saas_router in (
    saas_auth_router, saas_profile_router, saas_jobs_router, saas_growth_router,
    saas_gmail_router, saas_billing_router, saas_assist_router, saas_admin_router,
):
    app.include_router(saas_router, prefix="/v1", tags=["saas"])


@app.on_event("startup")
def startup():
    init_db()
    if not config.api_token():
        logger.warning(
            "CAREER_OS_API_TOKEN is not set — all private routes will return 500. "
            "Set it before serving traffic."
        )
    logger.info(
        "Career OS API started (env=%s, demo_mode=%s, demo_routes=%s, db=%s)",
        config.env_name(),
        config.public_demo_mode(),
        config.demo_routes_enabled(),
        config.db_path(),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
