"""
agents/crew_tasks.py
One Task per agent. Tasks chain together — each uses the output of the previous.
"""
import os
from datetime import datetime
from crewai import Task

TODAY = datetime.now().strftime("%A, %B %d %Y")
ROLES = os.getenv("TARGET_ROLES", "Data Analyst")
NAME  = os.getenv("YOUR_NAME", "the candidate")
JOBS_PER_DAY = int(os.getenv("JOBS_PER_DAY", "10"))
FULL_APPLICATIONS = min(int(os.getenv("FULL_APPLICATIONS", "5")), JOBS_PER_DAY)
SALARY_TARGET = os.getenv("SALARY_TARGET", "$120,000-$150,000+")

# AI/tech companies that are always explicitly searched — regardless of TARGET_COMPANIES secret.
AI_TECH_COMPANIES = [
    "Anthropic", "OpenAI", "Google DeepMind", "Google Cloud", "Microsoft",
    "Meta AI", "Amazon AWS", "Databricks", "Snowflake", "dbt Labs",
]
_extra = os.getenv("TARGET_COMPANIES", "")
_all_companies = AI_TECH_COMPANIES + [c.strip() for c in _extra.split(",") if c.strip()]
COMPANIES_LIST = ", ".join(_all_companies)

def build_tasks(agents: dict) -> list:

    # ── Task 1: Scan job market ────────────────────────────
    task_scan = Task(
        description=(
            f"Today is {TODAY}. Search LinkedIn, Indeed, Glassdoor, and each company's careers page "
            f"for {ROLES} job postings (Data Analyst, Analytics Engineer, Data Engineer, "
            "ML Engineer, AI Engineer, BI Engineer).\n\n"
            f"PRIORITY COMPANIES — always search these specifically: {COMPANIES_LIST}. "
            "Include AI/ML data roles, developer relations, data science, and any "
            "data-platform or analytics-engineering openings at those companies. "
            f"At minimum 3 of the top {JOBS_PER_DAY} results should be from this priority list when open.\n\n"
            f"Find at least {JOBS_PER_DAY + 5} current postings total. "
            f"Prioritize roles paying {SALARY_TARGET} (senior/mid-senior). "
            "For each posting, extract required technical skills. Tally across all postings. Output:\n"
            "(A) Top 10 skills ranked by frequency across all postings.\n"
            "(B) The 5 most critical skill gaps for the candidate to reach those salary bands.\n"
            f"(C) The top {JOBS_PER_DAY} postings as a numbered list, each with: "
            "Company | Role Title | URL | Salary (if listed) | Top 3 Required Skills.\n\n"
            "REQUIRED FINAL STEP — LOG TO SHEETS: After producing section (C), call the "
            "log_to_sheets tool exactly once with a JSON array of all postings. Each item: "
            "{\"company\": ..., \"role\": ..., \"url\": ..., \"status\": \"Applied\", "
            "\"date_applied\": \"" + datetime.now().strftime("%Y-%m-%d") + "\", "
            "\"notes\": \"<salary> | <top required skill>\"}. "
            "These are real postings you just found — log them all in one call. "
            "Do not finish the task until you see the '✅ Logged N application(s)' confirmation."
        ),
        expected_output=(
            f"(A) Top 10 skill frequencies, (B) 5 skill gaps, "
            f"(C) numbered list of top {JOBS_PER_DAY} postings with company/role/URL/salary/skills, "
            "AND confirmation that all postings were logged to Google Sheets."
        ),
        agent=agents["skills_scout"],
    )

    # ── Task 2: Daily data project ─────────────────────────
    task_data = Task(
        description=(
            f"Today is {TODAY}. Based on the skill gaps and job postings from Task 1, "
            f"propose ONE concrete, build-worthy PORTFOLIO PROJECT that would impress recruiters "
            f"for {SALARY_TARGET} data/analytics/ML engineering roles, especially at the AI companies "
            f"on today's list ({', '.join(AI_TECH_COMPANIES[:5])}, etc.). "
            "Lean into the candidate's healthcare-domain edge AND the AI/data-engineering angle. "
            "Provide: (1) project title + business question it answers, "
            "(2) a REAL public dataset (name + source URL from CMS, Kaggle, data.gov, HHS, etc.), "
            "(3) approach and tech stack (SQL/Python/dbt/cloud/ML/LLM as fits), "
            "(4) starter Python (pandas) code showing how to load and begin the analysis, "
            "(5) which skills/certs it demonstrates and which companies would find it impressive. "
            "This is a CONCEPT for the candidate to build — it is not uploaded anywhere today."
        ),
        expected_output=(
            "A portfolio project concept: title, business question, real dataset + source URL, "
            "approach/tech stack (noting which AI/tech companies it targets), starter Python code, "
            "and the skills it demonstrates."
        ),
        agent=agents["data_analyst"],
        context=[task_scan],
    )

    # ── Task 3: Today's lesson ────────────────────────────
    task_lesson = Task(
        description=(
            f"Today is {TODAY}. Build {NAME} a comprehensive DAILY LESSON moving her toward "
            f"{SALARY_TARGET} Data / Analytics / ML / AI Engineering roles — especially at "
            f"AI-first companies like {', '.join(AI_TECH_COMPANIES[:4])}.\n\n"
            "ROTATE the focus day-to-day so that over ~2 weeks it covers the full target stack: "
            "SQL, Python, Power BI (semantic model + DAX + RLS), Snowflake, dbt, Azure data "
            "engineering (Data Factory, ADLS, Synapse), Databricks (Spark, Delta Lake), "
            "machine learning, and LLM/AI engineering. "
            "Prefer the tool she is currently building in her portfolio when relevant; "
            "otherwise advance the rotation. Pick ONE focused topic for today and produce in markdown:\n"
            "## Today's Focus (topic + why it matters for the salary target, 2 sentences)\n"
            "## Lesson Plan (numbered, timeboxed ~45-60 min agenda)\n"
            "## Step-by-Step How-To (exact hands-on steps + commented code/SQL)\n"
            "## Practice Exercise (one realistic healthcare/business problem)\n"
            "## Solution (worked answer with explanation)\n"
            "## Common Interview Questions — 5 real questions a hiring manager asks on TODAY'S topic. "
            "For EACH: a thorough senior-level answer covering the concept, WHY it matters, a concrete "
            "example from healthcare/data, and the trade-off/gotcha interviewers probe for.\n"
            "## Check Yourself (3 quick questions)\n"
            "## Free Resource (one specific link)\n"
            "## Tomorrow's Preview (one line).\n"
            "Be concrete and senior-level — she should be able to both DO the skill today AND "
            "confidently answer for it in an interview."
        ),
        expected_output=(
            "A daily lesson in markdown: timeboxed agenda, step-by-step how-to with code, "
            "practice + solution, FIVE in-depth interview Q&As, self-check, and next-day preview."
        ),
        agent=agents["tutor"],
        context=[task_scan],
    )

    # ── Task 4: Apply to jobs ─────────────────────────────
    task_apply = Task(
        description=(
            f"Today is {TODAY}. Using the job postings list produced in Task 1, write tailored "
            f"application materials for the {FULL_APPLICATIONS} best-fit / highest-paying roles "
            f"(prioritize {SALARY_TARGET} and AI/tech companies: {', '.join(AI_TECH_COMPANIES[:5])}).\n\n"
            "FOR EACH ROLE, do these three things:\n"
            "1. MIRROR THE JOB POSTING: Pull the exact required skills and keywords from the posting. "
            "List which ones match the candidate's background and which are growth areas.\n"
            "2. TAILORED RESUME BULLETS (3): Each bullet must start with a strong action verb, "
            "quantify impact where possible (%, $, scale), and use the exact keywords/tools from "
            "that specific posting. Draw from: 5+ years at Optum/UHG (coding quality, claims "
            "analytics, HCC risk adjustment, 95%+ accuracy, auditing team of 20), CorroHealth, "
            "the Career OS AI system project, the MedCoding AI product, and the Healthcare Fraud "
            "Risk and Revenue Integrity portfolio projects.\n"
            "3. COVER LETTER (3 paragraphs, under 200 words): Para 1 — why THIS company/role "
            "specifically (reference what makes them unique); Para 2 — the single strongest "
            "experience match using STAR structure; Para 3 — one sentence on fit + call to action. "
            "For AI companies, lead with the Career OS and MedCoding AI projects.\n\n"
            "Do NOT fabricate experience or invent tools she hasn't used. "
            "For stretch roles (AI research, ML engineering), be honest about growth areas and "
            "frame the healthcare + automation background as the differentiator."
        ),
        expected_output=(
            f"For each of the top {FULL_APPLICATIONS} roles: a keyword match analysis, "
            "3 tailored resume bullets mirroring the posting's language, "
            "and a 3-paragraph cover letter under 200 words."
        ),
        agent=agents["job_applicant"],
        context=[task_scan],
    )

    # ── Task 5: Interview prep ─────────────────────────────
    task_interview = Task(
        description=(
            f"Today is {TODAY}. Using the top job postings and skill gaps from Task 1, "
            f"generate a daily interview prep session for {NAME}. "
            "Create exactly 10 questions across these 5 categories (2 each):\n\n"
            "**1. Behavioral (STAR format)** — Questions about teamwork, conflict, leadership, "
            "failure, or prioritization. Write model answers using STAR format drawn from "
            f"{NAME}'s real experience at Optum/UHG, CorroHealth, or MBA projects. "
            "Include specific metrics (95%+ accuracy, team of 20, etc.).\n\n"
            "**2. Technical — Engineering Stack (rotate tool day to day)** — One realistic "
            "technical question on a tool from her target stack, rotating across: advanced SQL "
            "(window functions, query optimization, partition pruning), Snowflake, Azure "
            "(Data Factory/Synapse), Databricks/Spark + Delta, dbt, Python data pipelines. "
            "Prefer the tool she is currently building (Snowflake/Azure first). "
            f"Give the correct answer with explanation and trade-off. Aim at {SALARY_TARGET} level.\n\n"
            "**3. System Design / Architecture** — A realistic data-engineering design prompt "
            "(e.g. 'design a pipeline to ingest daily Medicare claims into Snowflake with quality "
            "checks and incremental loads'). Senior-level answer: requirements → architecture → "
            "tool choices + WHY → scale, cost, data quality.\n\n"
            "**4. Case Study / Business Scenario** — A realistic business problem "
            "(e.g. 'Revenue dropped 15% in Q3 — walk me through your analysis'). "
            "Structured answer showing analytical thinking and stakeholder communication.\n\n"
            "**5. Questions to Ask the Interviewer** — Two smart, specific questions that show "
            "research and genuine interest (not generic questions).\n\n"
            "For EVERY answer: confident and specific, first person, lead with impact, "
            "acknowledge growth areas honestly. Under 200 words each."
        ),
        expected_output=(
            "10 interview questions with polished answers across 5 categories, "
            "personalized to the candidate's real background."
        ),
        agent=agents["interview_coach"],
        context=[task_scan],
    )

    # ── Task 6: Compile briefing ──────────────────────────
    task_brief = Task(
        description=(
            f"Today is {TODAY}. Compile all agent outputs into one Notion daily briefing for {NAME}. "
            "Use the write_to_notion tool. Format with these exact sections:\n"
            "# Daily Career Briefing — {TODAY}\n"
            "## Today's Market Signal (top 3 skill gaps from Task 1)\n"
            "## Today's Lesson & Interview Q&A (lesson topic + the 5 interview questions with answers)\n"
            "## Jobs Applied Today (table: company | role | status — from Task 4 apply list)\n"
            "## This Week's Project Idea (portfolio project concept + dataset from Task 2)\n"
            "## Interview Prep (today's 10 practice Q&As by category from Task 5)\n"
            "## Tomorrow's Focus (one sentence: what to practice)\n\n"
            "Keep it to what a busy person will actually read in 5 minutes. "
            "Plain English, no filler."
        ),
        expected_output=(
            "Confirmation that the Notion page was created successfully, with the page title."
        ),
        agent=agents["orchestrator"],
        context=[task_scan, task_data, task_lesson, task_apply, task_interview],
    )

    return [task_scan, task_data, task_lesson, task_apply, task_interview, task_brief]
