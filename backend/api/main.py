import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.db import init_db
from api.routes.runs import router as runs_router
from api.routes.briefings import router as briefings_router
from api.routes.analytics import router as analytics_router
from api.routes.interview import router as interview_router
from api.ws import router as ws_router

app = FastAPI(title="Career OS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs_router, prefix="/runs", tags=["runs"])
app.include_router(briefings_router, prefix="/briefings", tags=["briefings"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(interview_router, prefix="/interview", tags=["interview"])
app.include_router(ws_router, tags=["websocket"])


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}
