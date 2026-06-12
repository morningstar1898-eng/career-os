import os
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from api.db import get_db
from api.models import InterviewStartRequest, InterviewAnswerRequest, InterviewSessionResponse

router = APIRouter()

CATEGORIES = ["behavioral", "technical", "domain", "case_study", "questions_to_ask"]


@router.post("/start", response_model=InterviewSessionResponse)
def start_interview(req: InterviewStartRequest):
    if req.category not in CATEGORIES:
        raise HTTPException(400, f"Category must be one of: {CATEGORIES}")

    import litellm
    prompt = _build_question_prompt(req.category)
    response = litellm.completion(
        model="anthropic/claude-haiku-4-5-20251001",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.7,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    question = response.choices[0].message.content.strip()

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO interview_sessions (started_at, category, question) VALUES (?, ?, ?)",
            (datetime.utcnow().isoformat(), req.category, question),
        )
        session_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        return InterviewSessionResponse(**dict(row))


@router.post("/answer", response_model=InterviewSessionResponse)
def submit_answer(req: InterviewAnswerRequest):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (req.session_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Session not found")

    import litellm
    prompt = _build_scoring_prompt(dict(row)["question"], dict(row)["category"], req.user_answer)
    response = litellm.completion(
        model="anthropic/claude-haiku-4-5-20251001",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.3,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
    )
    feedback_raw = response.choices[0].message.content.strip()

    try:
        feedback_data = json.loads(feedback_raw)
        score = feedback_data.get("score", 5)
        feedback = feedback_data.get("feedback", feedback_raw)
    except json.JSONDecodeError:
        score = 5
        feedback = feedback_raw

    with get_db() as conn:
        conn.execute(
            "UPDATE interview_sessions SET user_answer = ?, ai_feedback = ?, score = ? WHERE id = ?",
            (req.user_answer, feedback, score, req.session_id),
        )
        row = conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (req.session_id,)).fetchone()
        return InterviewSessionResponse(**dict(row))


@router.get("/history")
def get_interview_history(limit: int = 20):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM interview_sessions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [InterviewSessionResponse(**dict(r)) for r in rows]


def _build_question_prompt(category: str) -> str:
    name = os.getenv("YOUR_NAME", "the candidate")
    prompts = {
        "behavioral": f"Generate one realistic behavioral interview question for a Data Analyst role. The candidate is {name}, transitioning from healthcare coding. Ask about teamwork, conflict resolution, or leadership. Just the question, nothing else.",
        "technical": "Generate one realistic SQL or Python technical interview question for a Data Analyst role. Medium difficulty. Just the question and any setup context needed, nothing else.",
        "domain": "Generate one interview question about data tools/concepts (Tableau, ETL, data warehousing, or healthcare analytics). Just the question, nothing else.",
        "case_study": "Generate one case study interview question for a Data Analyst. Present a business scenario (e.g., revenue dropped, user churn increased) and ask the candidate to walk through their analysis approach. Just the scenario and question, nothing else.",
        "questions_to_ask": "Generate one smart, specific question that a Data Analyst candidate should ask their interviewer to show research and genuine interest. Just the question, nothing else.",
    }
    return prompts.get(category, prompts["behavioral"])


def _build_scoring_prompt(question: str, category: str, answer: str) -> str:
    return f"""Score this interview answer on a scale of 1-10 and provide specific feedback.

Question ({category}): {question}

Candidate's answer: {answer}

Respond in JSON format ONLY:
{{"score": <1-10>, "feedback": "<2-3 sentences of specific, actionable feedback>", "model_answer": "<a strong example answer in 3-4 sentences>"}}"""
