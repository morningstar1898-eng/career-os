from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RunResponse(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    status: str
    trigger: str
    stage: Optional[str] = None
    error_message: Optional[str] = None


class RunTriggerRequest(BaseModel):
    trigger: str = "manual"


class BriefingResponse(BaseModel):
    id: int
    run_id: Optional[int] = None
    date: str
    content_json: str


class MetricsResponse(BaseModel):
    date: str
    jobs_applied: int
    skills_gap_count: int
    interview_score: float
    portfolio_items: int


class InterviewStartRequest(BaseModel):
    category: str = "behavioral"


class InterviewAnswerRequest(BaseModel):
    session_id: int
    user_answer: str


class InterviewSessionResponse(BaseModel):
    id: int
    started_at: str
    category: str
    question: str
    user_answer: Optional[str] = None
    ai_feedback: Optional[str] = None
    score: Optional[float] = None
