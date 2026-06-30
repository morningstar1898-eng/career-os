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

# AI/tech companies always searched — regardless of TARGET_COMPANIES secret.
AI_TECH_COMPANIES = [
    "Anthropic", "OpenAI", "Google DeepMind", "Google Cloud", "Microsoft",
    "Meta AI", "Amazon AWS", "Databricks", "Snowflake", "dbt Labs",
]
# Internal employer — candidate is a current Optum/UHG employee. These are searched
# via the internal careers site (careers.unitedhealthgroup.com) in addition to LinkedIn.
INTERNAL_COMPANIES = ["Optum", "UnitedHealth Group", "OptumInsight", "Optum Health"]

_extra = os.getenv("TARGET_COMPANIES", "")
_all_companies = INTERNAL_COMPANIES + AI_TECH_COMPANIES + [c.strip() for c in _extra.split(",") if c.strip()]
COMPANIES_LIST = ", ".join(_all_companies)

def build_tasks(agents: dict) -> list:

    # ── Task 1: Scan job market ────────────────────────────
    task_scan = Task(
        description=(
            f"Today is {TODAY}. Search for {ROLES} job postings "
            "(Data Analyst, Analytics Engineer, Data Engineer, ML Engineer, AI Engineer, BI Engineer).\n\n"
            "SEARCH SOURCES — use all of these:\n"
            "  • careers.unitedhealthgroup.com — MUST search this directly for Optum/UHG internal roles. "
            "    Search 'data analyst', 'data engineer', 'analytics engineer', 'business intelligence'. "
            "    The candidate is a CURRENT OPTUM EMPLOYEE so internal postings are the highest priority.\n"
            "  • LinkedIn, Indeed, Glassdoor — for external roles\n"
            "  • Direct careers pages for: Anthropic (anthropic.com/careers), OpenAI (openai.com/careers), "
            "    Google (careers.google.com), Microsoft (careers.microsoft.com), Databricks, Snowflake\n\n"
            f"PRIORITY ORDER for the top {JOBS_PER_DAY} list:\n"
            "  1. Optum/UHG INTERNAL roles (careers.unitedhealthgroup.com) — aim for at least 3\n"
            "  2. AI/tech companies (Anthropic, OpenAI, Google, Microsoft, Databricks) — aim for 3-4\n"
            "  3. Best-fit external healthcare/data roles — remaining slots\n\n"
            f"Prioritize {SALARY_TARGET} (senior/mid-senior). "
            "For each posting extract required technical skills. Tally across all postings. Output:\n"
            "(A) Top 10 skills ranked by frequency.\n"
            "(B) The 5 most critical skill gaps.\n"
            f"(C) Top {JOBS_PER_DAY} postings as a numbered list — Company | Role | URL | Salary | "
            "Top 3 Required Skills | Internal? (yes/no).\n\n"
            "REQUIRED FINAL STEP — LOG TO SHEETS: Call log_to_sheets once with a JSON array. "
            "Each item: {\"company\": ..., \"role\": ..., \"url\": ..., \"status\": \"Applied\", "
            "\"date_applied\": \"" + datetime.now().strftime("%Y-%m-%d") + "\", "
            "\"notes\": \"INTERNAL | <salary> | <top skill>\" for Optum/UHG roles, "
            "else \"<salary> | <top skill>\"}. "
            "Do not finish until you see the '✅ Logged N application(s)' confirmation."
        ),
        expected_output=(
            f"(A) Top 10 skill frequencies, (B) 5 skill gaps, "
            f"(C) numbered list of top {JOBS_PER_DAY} postings with internal/external flag, "
            "AND Sheets logging confirmation."
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
            f"Today is {TODAY}. Build {NAME} a DEEP, ACTIONABLE DAILY LESSON advancing her toward "
            f"{SALARY_TARGET} Data / Analytics / ML / AI Engineering roles. "
            "CHECK your lesson history (in your goal) and pick a topic NOT recently covered.\n\n"
            "STACK ROTATION (pick one area that hasn't been covered recently):\n"
            "  SQL: window functions, CTEs, query optimization, partitioning, execution plans\n"
            "  Python: pandas advanced (groupby/reshape/merge), numpy, matplotlib, pipeline patterns\n"
            "  Power BI: DAX measures vs. calculated columns, semantic model design, RLS, Row Context\n"
            "  Snowflake: clustering keys, Time Travel, Zero-Copy Clone, Streams + Tasks, cost control\n"
            "  dbt: incremental models, sources + refs, tests, macros, snapshots, lineage\n"
            "  Azure: ADF watermark pattern, ADLS Gen2 hierarchy, Synapse dedicated vs serverless, Purview\n"
            "  Databricks: Delta Lake (ACID, Z-order, VACUUM), Spark joins, structured streaming, Unity Catalog\n"
            "  ML: feature engineering, scikit-learn pipelines, cross-validation, class imbalance in claims data\n"
            "  LLM/AI: prompt engineering, RAG pipelines, tool/function calling, agent frameworks (CrewAI)\n\n"
            "DEPTH REQUIREMENTS — this is not a blog post, it is a complete training module:\n"
            "## Today's Focus\n"
            "  Topic name + why it unlocks the salary target (2 sentences). "
            "  State the specific skill gap it closes from Task 1.\n"
            "## Why This Matters in Healthcare Analytics\n"
            "  2-3 sentences tying the concept to claims data, HCC coding, revenue integrity, or fraud detection. "
            "  This is the candidate's edge — connect every lesson to her domain.\n"
            "## Lesson Plan (timeboxed, ~45-60 min)\n"
            "  Numbered steps with time estimates. Each step is a concrete action, not a vague topic.\n"
            "## Core Concept Explained\n"
            "  Explain the concept as if to a smart practitioner seeing it for the first time. "
            "  Use an analogy. Then show how it works with a healthcare-data example.\n"
            "## Step-by-Step How-To\n"
            "  COMPLETE, RUNNABLE code or SQL. Every non-obvious line must have an inline comment "
            "  explaining WHY, not just what. Use realistic healthcare data (claims, providers, ICD-10). "
            "  Minimum 30 lines of substantive code.\n"
            "## Practice Exercise\n"
            "  One realistic business scenario she might face at Optum/UHG or a new employer. "
            "  Specific: name the table, the business question, the expected output format.\n"
            "## Solution\n"
            "  Full worked answer with the code AND a plain-English explanation of each key decision.\n"
            "## Common Interview Questions — FIVE questions at senior depth\n"
            "  For EACH question provide ALL FOUR of:\n"
            "  (1) The textbook answer (what everyone says)\n"
            "  (2) The senior-level nuance (what separates a $90k answer from a $140k answer)\n"
            "  (3) A concrete example from healthcare/claims data\n"
            "  (4) The gotcha — what the interviewer is ACTUALLY testing for, and what trips candidates up\n"
            "## Check Yourself (3 quick diagnostic questions with answers)\n"
            "## Free Resource (one specific URL — real docs/tutorial, not a vague 'Google it')\n"
            "## Tomorrow's Preview (one sentence teaser for the next topic in the rotation)"
        ),
        expected_output=(
            "A complete daily training module in markdown: focus + healthcare context, "
            "timeboxed lesson plan, core concept explanation, ≥30 lines of commented runnable code, "
            "practice exercise + full solution, FIVE deep interview Q&As each with 4 layers of depth, "
            "self-check, resource link, and next-day preview."
        ),
        agent=agents["tutor"],
        context=[task_scan],
    )

    # ── Task 4: Apply to jobs ─────────────────────────────
    task_apply = Task(
        description=(
            f"Today is {TODAY}. Using the job postings list produced in Task 1, write tailored "
            f"application materials for the {FULL_APPLICATIONS} best-fit roles. "
            "PRIORITIZE in this order: (1) Optum/UHG internal roles, (2) AI/tech company roles, "
            "(3) best-fit external roles.\n\n"
            "═══════════════════════════════════════════════════════════\n"
            "OPTUM/UHG INTERNAL ROLES — completely different strategy:\n"
            "═══════════════════════════════════════════════════════════\n"
            "The candidate is a CURRENT OPTUM EMPLOYEE. Internal transfer applications "
            "have a fundamentally different goal: prove she's the obvious internal choice.\n\n"
            "1. INTERNAL KEYWORD MATCH: Identify the exact skills/tools in the Optum JD. "
            "Note which ones she already uses in her current Optum role (strongest signal) vs. "
            "skills she has built independently (strong) vs. growth areas (honest).\n\n"
            "2. INTERNAL RESUME BULLETS (3): Mirror the JD's exact language. Lead every bullet "
            "with a metric or outcome from her current Optum work. Examples of strong framing:\n"
            "   - 'Analyzed 500+ monthly coding audits across HCC and risk adjustment workflows, "
            "     producing the same type of claims-quality reporting this role requires'\n"
            "   - 'Validated production datasets for PHI compliance and coding accuracy across "
            "     payer review workflows — directly aligned with [team]'s data quality mandate'\n"
            "   Each bullet should end with a bridge: 'directly applicable to [role/team]'.\n\n"
            "3. INTERNAL COVER LETTER (3 paragraphs, under 180 words):\n"
            "   Para 1: 'As a current Optum [title] since May 2019, I'm applying for [role] "
            "   because [specific reason this team/work excites her].' Skip company overview.\n"
            "   Para 2: Name ONE specific Optum initiative, platform, or data challenge this "
            "   team owns, and connect her existing work directly to it. STAR: what she did, "
            "   the data/tools involved, the outcome in Optum terms.\n"
            "   Para 3: 'I'm ready to bring [her technical growth — Azure/Snowflake/Python] "
            "   to complement my deep knowledge of [Optum's claims/HCC/quality systems].' "
            "   One-line ask.\n\n"
            "═══════════════════════════════════════════════════════════\n"
            "ALL OTHER ROLES — standard tailored strategy:\n"
            "═══════════════════════════════════════════════════════════\n"
            "1. KEYWORD MATCH: Extract required skills from the JD, rate each as match/partial/gap.\n"
            "2. RESUME BULLETS (3): Action verb + metric + exact JD keywords. Draw from: "
            "5+ years at Optum/UHG (coding quality, claims analytics, HCC risk adjustment, "
            "95%+ accuracy, auditing 20-person team), Career OS AI system, MedCoding AI product, "
            "Healthcare Fraud Risk and Revenue Integrity portfolio projects.\n"
            "3. COVER LETTER (3 paragraphs, under 200 words): Para 1 — company-specific hook "
            "(why THIS company, not just any data role). Para 2 — strongest STAR match. "
            "Para 3 — fit + call to action. For AI companies, lead Para 1 with Career OS/MedCoding AI.\n\n"
            "Do NOT fabricate experience. For stretch roles, frame growth areas honestly.\n\n"
            "FINAL STEP — ATS SCORE: After writing materials for each role, add a one-line "
            "ATS summary: 'ATS Match: XX% — Keywords hit: [list] — Missing: [list]'. "
            "Count keyword hits by comparing your bullets + cover letter against the JD's "
            "required skills. This tells the candidate which applications are strong before she sends them."
        ),
        expected_output=(
            f"For each of the top {FULL_APPLICATIONS} roles:\n"
            "- Label: INTERNAL (Optum/UHG) or EXTERNAL\n"
            "- ATS Match score (%) with keywords hit and missing\n"
            "- Keyword match analysis (match / partial / gap per required skill)\n"
            "- 3 tailored resume bullets using the posting's exact language\n"
            "- Cover letter using the appropriate strategy (internal or external)"
        ),
        agent=agents["job_applicant"],
        context=[task_scan],
    )

    # ── Task 5: Interview prep ─────────────────────────────
    # Read weak category signal passed in from workflow (populated by the pre-run
    # step that queries /interview/history from the Azure backend).
    weak_category = os.getenv("WEAK_INTERVIEW_CATEGORY", "")
    weak_signal = (
        f"\n\nPRIORITY: Recent practice data shows the candidate scores LOWEST on "
        f"'{weak_category}' questions. Weight your 10 questions toward that category — "
        f"use 3 of the 10 slots for '{weak_category}' instead of 2."
    ) if weak_category else ""

    task_interview = Task(
        description=(
            f"Today is {TODAY}. Using the top job postings and skill gaps from Task 1, "
            f"generate a daily interview prep session for {NAME}.\n\n"
            "STEP 0 — SOURCE REAL COMPANY QUESTIONS FIRST:\n"
            "For each of the top 1-2 companies in today's job list, search for their actual "
            "interview process. Use queries like:\n"
            "  - '[Company] data analyst interview questions Glassdoor 2024'\n"
            "  - '[Company] data engineer phone screen questions'\n"
            "  - '[Company] analytics interview process Reddit'\n"
            "For Optum/UHG specifically search: 'Optum data analyst interview questions site:glassdoor.com'\n"
            "Use what you find to write questions that mirror what those companies ACTUALLY ask. "
            "If you can't find company-specific questions, write realistic questions for that role level.\n\n"
            "Create exactly 10 questions across these 5 categories (2 each):\n\n"
            "**1. Behavioral (STAR format)** — Draw from real questions those companies ask on "
            f"Glassdoor. Write model STAR answers from {NAME}'s real experience at Optum/UHG, "
            "CorroHealth, or MBA projects. Include specific metrics.\n\n"
            "**2. Technical — Engineering Stack** — Pull a realistic technical question from "
            "today's priority company interview reviews if found. Otherwise rotate across: "
            "advanced SQL, Snowflake, Azure (ADF/Synapse), Databricks, dbt, Python pipelines. "
            f"Give the full correct answer with the interviewer's intended test. {SALARY_TARGET} level.\n\n"
            "**3. System Design / Architecture** — A design prompt matching what today's top "
            "companies actually ask (search '[Company] system design interview data'). "
            "Senior-level answer: requirements → architecture → tool choices + WHY → scale/cost/quality.\n\n"
            "**4. Case Study / Business Scenario** — A realistic business problem from healthcare "
            "analytics or the company's domain. Structured analytical + stakeholder answer.\n\n"
            "**5. Questions to Ask the Interviewer** — Two smart, company-researched questions "
            "showing you know their specific tech stack, team structure, or current initiatives.\n\n"
            "For EVERY answer: first person, confident, specific, lead with impact, "
            f"acknowledge growth areas honestly. Under 200 words each.{weak_signal}"
        ),
        expected_output=(
            "10 interview questions with polished answers across 5 categories. "
            "At least 4 questions sourced from or inspired by real company interview reviews. "
            "Questions and answers personalized to the candidate's background and today's companies."
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
