"""Clean the raw CrewAI terminal output into a readable briefing.

Strips the box-drawing characters CrewAI prints, extracts the final briefing
block, and removes trailing tool/confirmation noise. Reads crew_output.txt and
prints the cleaned text to stdout (consumed by the daily workflow before it
posts to the dashboard API / email).
"""
import re
import sys

BOX_ONLY = re.compile(r"^[\s╭╮╰╯┌┐└┘├┤┬┴┼─━═║│|+•]*$")
LEAD_BAR = re.compile(r"^[ \t]*[│|] {0,2}")
TRAIL_BAR = re.compile(r"\s*[│|]\s*$")
MULTI_BLANK = re.compile(r"\n{3,}")

# Trailing meta/noise sections to drop (CrewAI confirmation chatter)
CUT_MARKERS = [
    "## CONFIRMATION",
    "# ✅ NOTION DAILY BRIEFING",
    "✅ **Notion Page",
    "NOTION DAILY BRIEFING CREATED",
]

# Markers that indicate the start of the actual briefing body
START_MARKERS = [
    "# Daily Career Briefing",
    "Daily Career Briefing —",
    "## Today's Market Signal",
    "TODAY'S MARKET SIGNAL",
]


def main() -> None:
    try:
        text = open("crew_output.txt", encoding="utf-8", errors="ignore").read()
    except FileNotFoundError:
        print("No briefing content available.")
        return

    # Jump to the final briefing block so we skip verbose agent/tool logs.
    start = -1
    for m in START_MARKERS:
        i = text.rfind(m)
        if i > start:
            start = i
    if start > 0:
        text = text[start:]

    cleaned_lines = []
    for ln in text.split("\n"):
        if BOX_ONLY.match(ln):
            continue
        s = LEAD_BAR.sub("", ln)
        s = TRAIL_BAR.sub("", s)
        cleaned_lines.append(s.rstrip())

    cleaned = "\n".join(cleaned_lines)

    for marker in CUT_MARKERS:
        idx = cleaned.find(marker)
        if idx != -1:
            cleaned = cleaned[:idx]

    cleaned = MULTI_BLANK.sub("\n\n", cleaned).strip()

    if not cleaned:
        cleaned = "Briefing generated — see Notion for full details."

    # Append the auto-submit outcome (written by auto_submit/run_auto_submit.py)
    # so the daily email always answers "what was actually submitted, with proof".
    try:
        report = open("submission_report.md", encoding="utf-8").read().strip()
        if report:
            cleaned += "\n\n" + report
    except FileNotFoundError:
        pass

    sys.stdout.write(cleaned)


if __name__ == "__main__":
    main()
