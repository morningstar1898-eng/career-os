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
JOBS_PER_DAY = int(os.getenv("JOBS_PER_DAY", "10"))

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
            f"Today is {TODAY}. Search for '{ROLES}' job postings on LinkedIn, Indeed, and Glassdoor. "
            f"Find at least {JOBS_PER_DAY + 5} real, current postings. {company_focus}"
            "For each, extract the required technical skills. "
            "Tally all skills across all postings. Output: "
            "(A) ranked list of top 10 skills by frequency, "
            "(B) the 5 most critical gaps for the candidate, "
            f"(C) the top {JOBS_PER_DAY} job postings with title, company, URL, and key requirements "
            "(prioritize the priority companies above when they have relevant openings)."
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
            f"Today is {TODAY}. Using the #1 skill gap identified in Task 1, "
            f"create a 30-minute learning session for {NAME}. Structure it as: "
            "## What it is (2 sentences), "
            "## Why employers want it (1 sentence), "
            "## Core concept with a real-world analogy, "
            "## Code example (SQL or Python, 15-20 lines, commented), "
            "## Practice exercise (one problem), "
            "## Solution, "
            "## One resource (free, include URL). "
            "Be concrete. Use a real dataset or business scenario in examples."
        ),
        expected_output=(
            "A complete 30-minute learning module in markdown with all 7 sections."
        ),
        agent=agents["tutor"],
        context=[task_scan],
    )

    # ── Task 4: Apply to jobs ─────────────────────────────
    task_apply = Task(
        description=(
            f"Today is {TODAY}. Take the top {JOBS_PER_DAY} job postings from Task 1. "
            f"For each posting: "
            "1) Write 3 tailored resume bullet points that match the job requirements, "
            f"   drawing on {NAME}'s {os.getenv('DEGREE','MBA in Data Analytics')} and data projects. "
            "2) Write a 3-paragraph cover letter (under 200 words). "
            "3) Log the application to Google Sheets using the log_to_sheets tool with: "
            "   company, role, url, status='Applied', date_applied=today, notes=key requirement. "
            f"Do this for all {JOBS_PER_DAY} jobs. Never invent experience. Focus on transferable skills. "
            "For stretch roles (e.g. AI/ML engineering or Anthropic Fellows), be honest about the "
            "candidate's growth areas while emphasizing transferable analytical and domain strengths."
        ),
        expected_output=(
            f"For each of {JOBS_PER_DAY} jobs: tailored bullet points, cover letter, and confirmation of Sheets log."
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
