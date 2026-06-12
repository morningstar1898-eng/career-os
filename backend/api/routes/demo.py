import json
from datetime import datetime, timedelta
from fastapi import APIRouter
from api.db import get_db

router = APIRouter()

SAMPLE_BRIEFING = {
    "market_signal": [
        "SQL proficiency (87% of postings)",
        "Python/pandas (72% of postings)",
        "Tableau or Power BI (65% of postings)"
    ],
    "lesson_summary": "Today's lesson: Window Functions in SQL — ROW_NUMBER, RANK, and LEAD/LAG for time-series analysis. Practiced with a healthcare claims dataset.",
    "jobs_applied": [
        {"company": "UnitedHealth Group", "role": "Senior Data Analyst", "status": "Applied"},
        {"company": "Humana", "role": "BI Analyst", "status": "Applied"},
        {"company": "Cigna", "role": "Analytics Engineer", "status": "Applied"},
        {"company": "Deloitte", "role": "Data Analyst - Healthcare", "status": "Applied"},
        {"company": "Epic Systems", "role": "Data Analyst", "status": "Applied"},
    ],
    "portfolio_update": "Analyzed CMS Medicare claims dataset (2.3M records). Generated 3 charts: cost distribution by DRG, readmission rates by region, length-of-stay trends. Uploaded to Azure Blob.",
    "interview_preview": "Practiced 10 questions across behavioral (STAR), technical SQL, domain knowledge, case study, and interviewer questions.",
    "tomorrow_focus": "Practice CTEs and subqueries — appeared in 4 of today's top job postings."
}


@router.post("/seed")
def seed_demo_data():
    with get_db() as conn:
        now = datetime.utcnow()

        for i in range(14):
            day = now - timedelta(days=13 - i)
            date_str = day.strftime("%Y-%m-%d")
            is_weekday = day.weekday() < 5

            if not is_weekday:
                continue

            conn.execute(
                "INSERT OR IGNORE INTO runs (started_at, finished_at, status, trigger) VALUES (?, ?, 'success', 'cron')",
                (day.replace(hour=13, minute=0).isoformat(), day.replace(hour=13, minute=8).isoformat()),
            )
            run_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

            conn.execute(
                "INSERT OR IGNORE INTO briefings (run_id, date, content_json) VALUES (?, ?, ?)",
                (run_id, date_str, json.dumps(SAMPLE_BRIEFING)),
            )

            jobs = 3 + (i % 4)
            gaps = max(3, 10 - i)
            score = min(8.5, 4.0 + i * 0.35)
            portfolio = 1 + (i // 2)
            conn.execute(
                "INSERT OR IGNORE INTO metrics (date, jobs_applied, skills_gap_count, interview_score, portfolio_items) VALUES (?, ?, ?, ?, ?)",
                (date_str, jobs, gaps, round(score, 1), portfolio),
            )

        categories = ["behavioral", "technical", "domain", "case_study", "questions_to_ask"]
        sample_questions = {
            "behavioral": ("Tell me about a time you had to present complex data to non-technical stakeholders.", "At Optum, I built a claims denial dashboard for our leadership team. I translated ICD-10 denial patterns into plain-language insights with a traffic-light system. The VP said it was the first time she actually understood why denials were spiking. Result: we reduced denial rates by 12% in Q3."),
            "technical": ("Write a SQL query to find the top 3 departments by average salary, excluding departments with fewer than 5 employees.", "SELECT department, AVG(salary) as avg_sal FROM employees GROUP BY department HAVING COUNT(*) >= 5 ORDER BY avg_sal DESC LIMIT 3;"),
            "domain": ("What's the difference between a star schema and a snowflake schema in data warehousing?", "A star schema has denormalized dimension tables directly connected to a central fact table — simpler queries, faster reads. A snowflake schema normalizes dimensions into sub-tables, saving storage but requiring more joins. For analytics workloads, I prefer star schemas because query performance matters more than storage savings."),
            "case_study": ("Your company's customer churn increased 20% last quarter. Walk me through how you'd investigate.", "First, I'd segment churn by customer cohort, product line, and region to find where it's concentrated. Then I'd look at behavioral signals — usage frequency, support tickets, billing issues — in the 90 days before churn. I'd compare churned vs retained customers to identify the strongest predictors. Finally, I'd present findings with a recommendation: if it's onboarding-related, improve the first 30 days; if it's pricing, test retention offers."),
            "questions_to_ask": ("What does the data stack look like here, and what's on the roadmap to change?", ""),
        }

        for cat in categories:
            q, a = sample_questions[cat]
            conn.execute(
                "INSERT INTO interview_sessions (started_at, category, question, user_answer, ai_feedback, score) VALUES (?, ?, ?, ?, ?, ?)",
                (now.isoformat(), cat, q, a if a else None, "Strong answer with specific examples." if a else None, 7.5 if a else None),
            )

    return {"status": "ok", "message": "Demo data seeded (14 days of metrics, briefings, and interview sessions)"}
