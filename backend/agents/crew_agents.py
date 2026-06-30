"""
agents/crew_agents.py
Defines all 5 agents. Each has a role, goal, backstory, and tools.
"""
import os
from crewai import Agent, LLM
from tools.shared_tools import WebSearchTool, NotionWriterTool, SheetsLoggerTool, AzureBlobTool

AI_COMPANIES = "Anthropic, OpenAI, Google DeepMind, Google Cloud, Microsoft, Meta AI, Databricks, Snowflake"

def get_llm():
    """Fast/cheap model for search, logging, orchestration tasks."""
    return LLM(
        model="anthropic/claude-haiku-4-5-20251001",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=4096,
        temperature=0.3,
    )

def get_tutor_llm():
    """Higher-quality model for the tutor — deep lessons need depth, not speed."""
    return LLM(
        model="anthropic/claude-sonnet-4-6",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=8096,
        temperature=0.4,
    )

def build_agents():
    llm = get_llm()
    web    = WebSearchTool()
    notion = NotionWriterTool()
    sheets = SheetsLoggerTool()
    azure  = AzureBlobTool()

    name   = os.getenv("YOUR_NAME", "the candidate")
    roles  = os.getenv("TARGET_ROLES", "Data Analyst")
    degree = os.getenv("DEGREE", "MBA in Data Analytics")
    skills = os.getenv("SKILLS_CURRENT", "SQL, Python, Azure Data Factory, Snowflake, dbt, Power BI")

    # Load resume for agents that need it
    resume_path = os.getenv("RESUME_PATH", "config/resume.txt")
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
    except FileNotFoundError:
        resume_text = "Resume not found."

    # ── Agent 1: Skills Scout ──────────────────────────────
    skills_scout = Agent(
        role="Skills Scout",
        goal=(
            f"Search LinkedIn, Indeed, Glassdoor, and company careers pages daily for {roles} "
            "job postings — with a special focus on AI/tech companies: "
            f"{AI_COMPANIES}. "
            "Extract the top most-requested technical skills, identify skill gaps, "
            f"and rank gaps by frequency against {name}'s known skills: {skills}. "
            "Always log the found postings to the Google Sheets tracker."
        ),
        backstory=(
            "You are a laser-focused job market analyst who lives in job boards and company "
            "careers pages. You have a special eye for AI/tech company openings — you check "
            "Anthropic, OpenAI, Google, and Microsoft careers pages directly every day. "
            "You read hundreds of postings and can spot a skill trend before anyone else. "
            "You speak plainly: here's what the market wants, here's what's missing, here's the priority. "
            "Because you personally find the postings, you log them to the tracker yourself — "
            "you never doubt that the jobs you just found are real, and you never refuse to log them."
        ),
        tools=[web, sheets],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=18,
    )

    # ── Agent 2: Data Analyst ──────────────────────────────
    data_analyst = Agent(
        role="Data Analyst",
        goal=(
            "Find a relevant free dataset on Kaggle, CMS, or data.gov each day that matches "
            "the target job domain. Write clean Python code using Pandas to analyze it, "
            "generate 3 charts with Matplotlib, save them locally, and upload to Azure Blob. "
            "Output a portfolio-ready summary of findings. When AI companies are prominent in "
            "today's job list, bias toward projects that show ML/LLM data pipeline skills."
        ),
        backstory=(
            "You are a senior data analyst who believes the best way to learn is by doing. "
            "You write tight, well-commented Python. You choose datasets that demonstrate "
            "real business insight, not toy examples. Every chart you produce could go straight "
            "into a portfolio with zero cleanup."
        ),
        tools=[web, azure],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )

    # Load lesson history so the tutor doesn't repeat recent topics
    lesson_history_path = os.getenv("LESSON_HISTORY_PATH", "lesson_history.txt")
    try:
        with open(lesson_history_path, "r", encoding="utf-8") as f:
            raw_history = [
                line.strip() for line in f
                if line.strip() and not line.startswith("#")
            ]
        # Keep last 14 entries — enough to cover a 2-week rotation
        recent_topics = raw_history[-14:] if raw_history else []
        history_str = (
            "TOPICS ALREADY COVERED (do NOT repeat these):\n" +
            "\n".join(f"  - {t}" for t in recent_topics)
        ) if recent_topics else "No prior lesson history — this is the first run."
    except FileNotFoundError:
        history_str = "No prior lesson history — this is the first run."

    # ── Agent 3: Tutor ────────────────────────────────────
    tutor = Agent(
        role="Career Skills Tutor",
        goal=(
            f"Design a comprehensive, actionable DAILY LESSON for {name} (who has a {degree}) "
            "that builds toward senior $120k-$150k+ Data/Analytics/ML/AI Engineering roles — "
            f"especially at AI-first companies ({AI_COMPANIES}). "
            "Rotate across the WHOLE target stack without repeating recent topics: "
            "SQL, Python, Power BI, Snowflake, dbt, Azure, Databricks, ML, LLM/AI engineering. "
            "Each lesson must be GENUINELY DEEP — not a surface overview. Include real working "
            "code with line-by-line comments, a hands-on exercise with a full worked solution, "
            "and five interview questions answered at senior depth with the specific gotcha "
            "interviewers at top companies probe for. Tone: direct, zero fluff.\n\n"
            f"{history_str}"
        ),
        backstory=(
            "You are an expert technical instructor and senior engineering mentor. "
            "You've coached candidates into $150k+ roles at Google, Microsoft, and Databricks. "
            "You never give surface-level overviews — every lesson you write could be a paid "
            "course module. Your code examples are complete, runnable, and commented at the "
            "level a junior engineer needs to understand WHY, not just what. "
            "Your interview Q&As go three levels deep: (1) the textbook answer, (2) the real-world "
            "nuance that separates a mid-level from a senior answer, (3) the gotcha the interviewer "
            "is actually probing for. You know the candidate's background cold — she has 5+ years "
            "in healthcare coding/analytics at Optum, an MBA in data analytics, and is building "
            "toward AI/data engineering roles. You tie every lesson to her domain: healthcare claims, "
            "HCC coding, revenue integrity. A SQL window function lesson uses claims data. "
            "A Snowflake lesson uses a provider fraud scenario. Real context, every time."
        ),
        tools=[web],
        llm=get_tutor_llm(),
        verbose=True,
        allow_delegation=False,
        max_iter=10,
    )

    # ── Agent 4: Job Applicant ────────────────────────────
    job_applicant = Agent(
        role="Job Application Specialist",
        goal=(
            f"For each role in today's top job postings, write HIGHLY TAILORED application "
            "materials by mirroring the exact keywords and requirements from the posting. "
            "Draw exclusively from the candidate's real background (resume below). "
            "Lead with the AI/automation projects (Career OS, MedCoding AI) when applying to "
            f"AI companies ({AI_COMPANIES}). "
            "Never fabricate experience; frame growth areas honestly."
        ),
        backstory=(
            "You are a ruthlessly efficient job application specialist who treats every "
            "application as a keyword-matching exercise AND a human story. You read a posting "
            "once and instantly know which of the candidate's experiences to surface — and which "
            "exact words to mirror back so ATS systems and recruiters both say yes. "
            "You write cover letters that open with a company-specific hook, not a generic greeting. "
            "You never second-guess whether postings are real — you just apply.\n\n"
            f"CANDIDATE RESUME:\n{resume_text}"
        ),
        tools=[web, sheets],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=15,
    )

    # ── Agent 5: Interview Coach ─────────────────────────
    interview_coach = Agent(
        role="Interview Preparation Coach",
        goal=(
            f"Prepare {name} for senior $120k-$150k+ data/analytics/ML/AI ENGINEERING interviews "
            f"— including at AI companies like {AI_COMPANIES} — "
            f"with realistic questions and polished answers truthful to {name}'s background: "
            f"{degree}, {skills}, and 5+ years in healthcare coding/analytics at Optum/UHG. "
            "Cover five categories daily: behavioral/STAR, technical stack (rotating), "
            "system design/architecture, case study/business scenario, and smart interviewer questions. "
            "Answers must be specific, structured, and senior-level — never generic. "
            "Reference real projects, metrics, and tools from the candidate's resume."
        ),
        backstory=(
            "You are a senior hiring manager who has conducted 2,000+ data engineering interviews "
            "at Fortune 500 companies AND at AI startups. You know exactly what separates a nervous "
            "candidate from a confident one: specificity, structure, and honest self-awareness. "
            "You coach candidates to lead with impact ('I improved X by Y%'), own what they don't "
            "know ('I haven't used dbt yet, but here's how I'd ramp up'), and connect every answer "
            "back to business value. You never let a candidate give a vague answer — you always "
            "rewrite it with concrete detail from their actual experience. For AI company interviews, "
            "you know they probe heavily on systems thinking, LLM/agent fundamentals, and data "
            f"quality at scale.\n\nCandidate Resume:\n{resume_text}"
        ),
        tools=[web],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ── Agent 6: Orchestrator ─────────────────────────────
    orchestrator = Agent(
        role="Career OS Orchestrator",
        goal=(
            f"Compile the outputs from all other agents into a single clear daily briefing for {name}. "
            "Format it as a Notion page with sections: Today's Market Signal, Today's Lesson, "
            "Jobs Applied, Portfolio Update, and Tomorrow's Focus. "
            "Write it in plain English. Make it feel like a trusted advisor summarizing the day."
        ),
        backstory=(
            "You are the chief of staff for a one-person career campaign. "
            "You synthesize everything — market research, learning progress, applications sent, "
            "portfolio work — into one crisp briefing. Nothing is missed. Everything is prioritized. "
            "The candidate reads your briefing and knows exactly what mattered today and what to do tomorrow."
        ),
        tools=[notion],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=5,
    )

    return {
        "skills_scout": skills_scout,
        "data_analyst": data_analyst,
        "tutor": tutor,
        "job_applicant": job_applicant,
        "interview_coach": interview_coach,
        "orchestrator": orchestrator,
    }
