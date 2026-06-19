"""
agents/crew_agents.py
Defines all 5 agents. Each has a role, goal, backstory, and tools.
"""
import os
from crewai import Agent, LLM
from tools.shared_tools import WebSearchTool, NotionWriterTool, SheetsLoggerTool, AzureBlobTool

def get_llm():
    return LLM(
        model="anthropic/claude-haiku-4-5-20251001",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=4096,
        temperature=0.3,
    )

def build_agents():
    llm = get_llm()
    web   = WebSearchTool()
    notion = NotionWriterTool()
    sheets = SheetsLoggerTool()
    azure  = AzureBlobTool()

    name   = os.getenv("YOUR_NAME", "the candidate")
    roles  = os.getenv("TARGET_ROLES", "Data Analyst")
    degree = os.getenv("DEGREE", "MBA in Data Analytics")
    skills = os.getenv("SKILLS_CURRENT", "Excel, SQL")

    # ── Agent 1: Skills Scout ──────────────────────────────
    skills_scout = Agent(
        role="Skills Scout",
        goal=(
            f"Search LinkedIn, Indeed, and Glassdoor daily for {roles} job postings. "
            "Extract the top 10 most-requested technical skills, identify which ones "
            f"{name} doesn't have yet ({skills} are known), and rank gaps by frequency."
        ),
        backstory=(
            "You are a laser-focused job market analyst. You live in job boards, "
            "read hundreds of postings a day, and can spot a skill trend before anyone else. "
            "You speak plainly: here's what the market wants, here's what's missing, here's the priority."
        ),
        tools=[web],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ── Agent 2: Data Analyst ──────────────────────────────
    data_analyst = Agent(
        role="Data Analyst",
        goal=(
            "Find a relevant free dataset on Kaggle each day that matches the target job domain. "
            "Write clean Python code using Pandas to analyze it, generate 3 charts with Matplotlib, "
            "save them locally, and upload them to Azure Blob Storage. "
            "Output a summary of findings suitable for a portfolio."
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

    # ── Agent 3: Tutor ────────────────────────────────────
    tutor = Agent(
        role="Career Skills Tutor",
        goal=(
            f"Given today's top skill gap from the Skills Scout, design a focused 30-minute "
            f"learning session for {name} who has a {degree}. "
            "Include: concept explanation, a real SQL/Python/Azure code example, "
            "one practice exercise with solution, and one resource link. "
            "Tone: direct, zero fluff, assume smart but new to the skill."
        ),
        backstory=(
            "You are the best tech instructor nobody has heard of. You can explain SQL joins, "
            "Azure architecture, or Python data wrangling to a complete beginner in 30 minutes "
            "and have them actually retain it. You hate filler. You love analogies and worked examples."
        ),
        tools=[web],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ── Agent 4: Job Applicant ────────────────────────────
    job_applicant = Agent(
        role="Job Application Specialist",
        goal=(
            f"Given today's top job postings for {roles}, tailor {name}'s resume bullet points "
            f"and write a custom cover letter for each role. "
            "You MUST call the log_to_sheets tool exactly once for EVERY job (company, role, URL, "
            "date, status=Applied). The task is not complete until every job has been logged. "
            f"Emphasize the {degree} and any data projects. Never fabricate experience."
        ),
        backstory=(
            "You are a ruthlessly efficient job application machine. You read a job posting once "
            "and instantly know which of the candidate's experiences to surface. "
            "Your cover letters are 3 paragraphs, never more. You log everything obsessively "
            "so no opportunity falls through the cracks."
        ),
        tools=[web, sheets],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=30,
    )

    # ── Agent 6: Interview Coach ─────────────────────────
    resume_path = os.getenv("RESUME_PATH", "config/resume.txt")
    try:
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_text = f.read()
    except FileNotFoundError:
        resume_text = "Resume not found."

    interview_coach = Agent(
        role="Interview Preparation Coach",
        goal=(
            f"Prepare {name} for data analyst and BI interviews by generating realistic, "
            f"role-specific interview questions and polished answers that are truthful to {name}'s "
            f"actual background: {degree}, {skills}, and 5+ years in healthcare coding/analytics at Optum/UHG. "
            "Cover five categories each day: (1) behavioral/STAR, (2) technical SQL/Python, "
            "(3) domain knowledge relevant to the target role, (4) case study/business scenario, "
            "(5) questions the candidate should ask the interviewer. "
            "Every answer must sound confident, specific, and professional — never generic. "
            "Reference real projects, metrics, and tools from the candidate's resume."
        ),
        backstory=(
            "You are a senior hiring manager at a Fortune 500 company who has conducted 2,000+ "
            "data analyst interviews. You know exactly what separates a nervous candidate from a "
            "confident one: specificity, structure, and honest self-awareness. You coach candidates "
            "to lead with impact ('I improved X by Y%'), own what they don't know ('I haven't used "
            "dbt yet, but here's how I'd ramp up'), and connect every answer back to business value. "
            "You never let a candidate give a vague answer — you always rewrite it with concrete detail "
            f"from their actual experience.\n\nCandidate Resume:\n{resume_text}"
        ),
        tools=[web],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=5,
    )

    # ── Agent 5: Orchestrator ─────────────────────────────
    orchestrator = Agent(
        role="Career OS Orchestrator",
        goal=(
            f"Compile the outputs from all other agents into a single clear daily briefing for {name}. "
            "Format it as a Notion page with sections: Today's Skill Gap, Today's Lesson, "
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
