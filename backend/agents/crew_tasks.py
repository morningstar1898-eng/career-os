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
COMPANIES = os.getenv("TARGET_COMPANIES", "")
JOBS_PER_DAY = int(os.getenv("JOBS_PER_DAY", "50"))
FULL_APPLICATIONS = min(int(os.getenv("FULL_APPLICATIONS", "15")), JOBS_PER_DAY)
SALARY_TARGET = os.getenv("SALARY_TARGET", "$120,000-$150,000+")

def build_tasks(agents: dict) -> list:

    # ── Task 1: Scan job market ────────────────────────────
    company_focus = (
        f"PRIORITY: also specifically search for openings at these companies: {COMPANIES}. "
        "Include AI/ML engineering and research roles, and Anthropic's Fellows program "
        "(fellowship/residency openings). Make sure at least 3 of these priority-company "
        "roles appear in the final list when any are open. "
        if COMPANIES else ""
    )
    task_scan = Task(
        description=(
            f"Today is {TODAY}. Search for job postings on LinkedIn, Indeed, and Glassdoor across "
            f"these role families: {ROLES} (i.e. Data Analyst, Analytics Engineer, Data Engineer, "
            f"Machine Learning Engineer, and AI Engineer). "
            f"Find at least {JOBS_PER_DAY + 10} real, current postings. {company_focus}"
            f"PRIORITIZE roles that pay {SALARY_TARGET} (senior / mid-senior level). "
            "For each, extract the required technical skills. Tally all skills across all postings. Output: "
            "(A) ranked list of top 10 skills by frequency, "
            "(B) the 5 most critical skill gaps for the candidate to reach those salary bands, "
            f"(C) the top {JOBS_PER_DAY} job postings with title, company, URL, salary (if listed), and key "
            "requirements — prioritize the priority companies and the highest-paying / best-fit roles first."
        ),
        expected_output=(
            f"A structured report with three sections: Top Skills Ranked, Skill Gaps, and Top {JOBS_PER_DAY} Job Postings."
        ),
        agent=agents["skills_scout"],
    )

    # ── Task 2: Daily data project ─────────────────────────
    task_data = Task(
        description=(
            f"Today is {TODAY}. Based on the job domain from Task 1's skill gaps, "
            "find a relevant free dataset on Kaggle (search for it). "
            "Write complete Python code (pandas + matplotlib) that: "
            "1) loads the dataset, 2) cleans it, 3) produces 3 insightful charts, "
            "4) saves charts as PNG files to ./outputs/, 5) prints a 3-sentence insight summary. "
            "The code must be production-quality with comments. "
            "Then upload each chart PNG to Azure Blob Storage using the upload_to_azure tool. "
            "Output: the full Python code block + the insight summary + Azure URLs."
        ),
        expected_output=(
            "Complete runnable Python code, a 3-sentence insight summary, and Azure blob URLs for each chart."
        ),
        agent=agents["data_analyst"],
        context=[task_scan],
    )

    # ── Task 3: Today's lesson ────────────────────────────
    task_lesson = Task(
        description=(
            f"Today is {TODAY}. Build {NAME} a concrete DAILY LESSON PLAN that moves her toward "
            f"{SALARY_TARGET} Data/Analytics/ML/AI Engineering roles. Target the #1 skill gap from "
            "Task 1 (rotate focus day to day so over time it builds a curriculum: SQL → Python → dbt "
            "→ data modeling/warehousing → ML basics → LLM/AI engineering). Structure it as a "
            "step-by-step plan she can DO today, in markdown:\n"
            "## Today's Focus (skill + why it matters for the salary target, 2 sentences)\n"
            "## Lesson Plan (a numbered, timeboxed agenda for ~45-60 min, e.g. 1. Concept 10m, "
            "2. Guided example 15m, 3. Hands-on 25m, 4. Review 10m)\n"
            "## Step-by-Step How-To (the actual instructions to follow for the hands-on part — "
            "exact steps, commands, and a commented code example in SQL/Python/dbt as relevant)\n"
            "## Practice Exercise (one realistic problem using a healthcare or business dataset)\n"
            "## Solution (worked answer with explanation)\n"
            "## Check Yourself (3 questions to confirm understanding)\n"
            "## Free Resource (one specific link) and ## Tomorrow's Preview (one line). "
            "Be concrete and actionable — she should be able to follow the steps without further research."
        ),
        expected_output=(
            "A complete, actionable daily lesson plan in markdown with timeboxed agenda, "
            "step-by-step how-to instructions, a practice exercise + solution, and next-day preview."
        ),
        agent=agents["tutor"],
        context=[task_scan],
    )

    # ── Task 4: Apply to jobs ─────────────────────────────
    task_apply = Task(
        description=(
            f"Today is {TODAY}. Work the top {JOBS_PER_DAY} job postings from Task 1, prioritizing "
            f"roles paying {SALARY_TARGET} and the priority companies.\n\n"
            f"STEP 1 — LOG ALL {JOBS_PER_DAY} (most important; do this first): Make ONE call to the "
            "log_to_sheets tool passing a JSON ARRAY of all the jobs. Each array item: "
            "{{company, role, url, status:'Applied', date_applied:today, notes:(key requirement + "
            "one-line fit note)}}. The tool accepts an array, so log them all in a single call "
            f"(split into 2-3 calls only if needed). Do NOT finish until all {JOBS_PER_DAY} are logged — "
            "logging the full pipeline is the #1 deliverable.\n\n"
            f"STEP 2 — FULL APPLICATION MATERIALS for the {FULL_APPLICATIONS} best-fit / highest-paying "
            f"roles: for each, write 3 tailored resume bullet points (drawing on {NAME}'s "
            f"{os.getenv('DEGREE','MBA in Data Analytics')}, healthcare-analytics experience, and data "
            "projects) and a 3-paragraph cover letter under 200 words.\n\n"
            "Never invent experience. Emphasize transferable analytical + healthcare-domain strengths. "
            "For stretch AI/ML roles (incl. Anthropic Fellows), be honest about growth areas while "
            "showing a credible path."
        ),
        expected_output=(
            f"Confirmation that all {JOBS_PER_DAY} applications were logged to Sheets, plus full tailored "
            f"bullet points and cover letters for the top {FULL_APPLICATIONS} roles."
        ),
        agent=agents["job_applicant"],
        context=[task_scan],
    )

    # ── Task 5: Interview prep ─────────────────────────────
    task_interview = Task(
        description=(
            f"Today is {TODAY}. Using the top job postings and skill gaps from Task 1, "
            f"generate a daily interview prep session for {NAME}. Create exactly 10 questions "
            "across these 5 categories (2 each):\n\n"
            "**1. Behavioral (STAR format)** — Questions about teamwork, conflict, leadership, "
            "failure, or prioritization. Write model answers using STAR format (Situation, Task, "
            f"Action, Result) drawn from {NAME}'s real experience at Optum/UHG, CorroHealth, "
            "or MBA projects. Include specific metrics (95%+ accuracy, team of 20, etc.).\n\n"
            "**2. Technical SQL/Python** — Write a realistic SQL query or Python code question "
            "that a hiring manager would ask for a Data Analyst role. Provide the correct answer "
            f"with explanation. Match the difficulty to {NAME}'s current skill level.\n\n"
            "**3. Domain/Tool Knowledge** — Questions about Tableau, Power BI, Excel, "
            "data pipelines, ETL, data warehousing, or healthcare analytics. Answers should "
            "reference real tools and workflows the candidate has used.\n\n"
            "**4. Case Study / Business Scenario** — Present a realistic business problem "
            "(e.g., 'Revenue dropped 15% in Q3 — walk me through your analysis') and write "
            "a structured answer showing analytical thinking and stakeholder communication.\n\n"
            "**5. Questions to Ask the Interviewer** — Two smart, specific questions that show "
            "research and genuine interest (not generic 'what's the culture like' questions).\n\n"
            "For EVERY answer: sound confident and specific, not rehearsed. Use first person. "
            "Lead with impact. Acknowledge growth areas honestly. Keep each answer under 200 words."
        ),
        expected_output=(
            "A structured interview prep document with 10 questions and polished answers "
            "across 5 categories, all personalized to the candidate's real background."
        ),
        agent=agents["interview_coach"],
        context=[task_scan],
    )

    # ── Task 6: Compile briefing ──────────────────────────
    task_brief = Task(
        description=(
            f"Today is {TODAY}. Compile all agent outputs into one Notion daily briefing for {NAME}. "
            "Use the write_to_notion tool. Format with these exact sections: "
            "# Daily Career Briefing — {TODAY}, "
            "## Today's Market Signal (top 3 skill gaps), "
            "## Today's Lesson (summary of lesson + link to full content), "
            "## Jobs Applied Today (table: company | role | status), "
            "## Portfolio Update (dataset analyzed + chart URLs), "
            "## Interview Prep (today's 10 practice Q&As by category), "
            "## Tomorrow's Focus (one sentence: what to practice). "
            "Keep it to what a busy person will actually read in 5 minutes."
        ),
        expected_output=(
            "Confirmation that the Notion page was created successfully, with the page title."
        ),
        agent=agents["orchestrator"],
        context=[task_scan, task_data, task_lesson, task_apply, task_interview],
    )

    return [task_scan, task_data, task_lesson, task_apply, task_interview, task_brief]
