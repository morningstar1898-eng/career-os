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

def build_tasks(agents: dict) -> list:

    # ── Task 1: Scan job market ────────────────────────────
    task_scan = Task(
        description=(
            f"Today is {TODAY}. Search for '{ROLES}' job postings on LinkedIn, Indeed, and Glassdoor. "
            "Find at least 10 real, current postings. For each, extract the required technical skills. "
            "Tally all skills across all postings. Output: "
            "(A) ranked list of top 10 skills by frequency, "
            "(B) the 5 most critical gaps for someone new to the field, "
            "(C) the top 5 job postings with title, company, URL, and key requirements."
        ),
        expected_output=(
            "A structured report with three sections: Top Skills Ranked, Skill Gaps, and Top 5 Job Postings."
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
            f"Today is {TODAY}. Take the top 5 job postings from Task 1. "
            f"For each posting: "
            "1) Write 3 tailored resume bullet points that match the job requirements, "
            f"   drawing on {NAME}'s {os.getenv('DEGREE','MBA in Data Analytics')} and data projects. "
            "2) Write a 3-paragraph cover letter (under 200 words). "
            "3) Log the application to Google Sheets using the log_to_sheets tool with: "
            "   company, role, url, status='Applied', date_applied=today, notes=key requirement. "
            "Do this for all 5 jobs. Never invent experience. Focus on transferable MBA skills."
        ),
        expected_output=(
            "For each of 5 jobs: tailored bullet points, cover letter, and confirmation of Sheets log."
        ),
        agent=agents["job_applicant"],
        context=[task_scan],
    )

    # ── Task 5: Compile briefing ──────────────────────────
    task_brief = Task(
        description=(
            f"Today is {TODAY}. Compile all agent outputs into one Notion daily briefing for {NAME}. "
            "Use the write_to_notion tool. Format with these exact sections: "
            "# Daily Career Briefing — {TODAY}, "
            "## Today's Market Signal (top 3 skill gaps), "
            "## Today's Lesson (summary of lesson + link to full content), "
            "## Jobs Applied Today (table: company | role | status), "
            "## Portfolio Update (dataset analyzed + chart URLs), "
            "## Tomorrow's Focus (one sentence: what to practice). "
            "Keep it to what a busy person will actually read in 3 minutes."
        ),
        expected_output=(
            "Confirmation that the Notion page was created successfully, with the page title."
        ),
        agent=agents["orchestrator"],
        context=[task_scan, task_data, task_lesson, task_apply],
    )

    return [task_scan, task_data, task_lesson, task_apply, task_brief]
