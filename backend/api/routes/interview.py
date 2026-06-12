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
    question = _clean_question(response.choices[0].message.content.strip())

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
        clean = feedback_raw
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        feedback_data = json.loads(clean)
        score = feedback_data.get("score", 5)
        feedback = json.dumps(feedback_data)
    except (json.JSONDecodeError, IndexError):
        score = 5
        feedback = json.dumps({"whats_good": "", "how_to_improve": feedback_raw, "model_answer": "", "key_takeaway": ""})

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
    base = "Reply with ONLY the question text. No titles, headers, markdown, labels, bullet points, or formatting. Plain text only."
    prompts = {
        "behavioral": f"Generate one realistic behavioral interview question for a Data Analyst role. The candidate is {name}, transitioning from healthcare coding. Ask about teamwork, conflict resolution, or leadership. {base}",
        "technical": f"Generate one realistic SQL or Python technical interview question for a Data Analyst role. Medium difficulty. If you need to describe a table schema, write it as a plain sentence like 'You have a table called orders with columns: id, customer_id, amount, date.' Do NOT use code blocks, backticks, or markdown. {base}",
        "domain": f"Generate one interview question about data tools or concepts such as Tableau, ETL, data warehousing, or healthcare analytics. {base}",
        "case_study": f"Generate one case study interview question for a Data Analyst. Present a short business scenario and ask the candidate to walk through their analysis approach. {base}",
        "questions_to_ask": f"Generate one smart, specific question that a Data Analyst candidate should ask their interviewer to show research and genuine interest. {base}",
    }
    return prompts.get(category, prompts["behavioral"])


def _build_scoring_prompt(question: str, category: str, answer: str) -> str:
    return f"""You are a supportive senior interview coach helping a data analyst candidate improve. Score their answer and teach them.

Question ({category}): {question}

Candidate's answer: {answer}

Respond in JSON format ONLY with these fields:
{{
  "score": <1-10>,
  "whats_good": "<1-2 sentences on what the candidate did well, even if the answer was weak. Find something positive.>",
  "how_to_improve": "<2-3 sentences of specific, actionable coaching. Tell them exactly what to add, remove, or restructure. Be encouraging, not critical.>",
  "model_answer": "<Write a complete, polished example answer as if the candidate were saying it in an interview. Use first person. Be specific with real examples. For technical questions, walk through the logic step by step in plain English first, then provide the code/query. Keep it under 200 words.>",
  "key_takeaway": "<One sentence the candidate should remember for next time.>"
}}"""


def _clean_question(text: str) -> str:
    import re
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*([^*]*)\*\*", r"\1", text)
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
