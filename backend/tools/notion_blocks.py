"""
tools/notion_blocks.py
Markdown lines → Notion block payloads. Kept free of heavy imports
(CrewAI, notion_client) so the CI test suite can cover it.
"""

# Notion rejects any single rich_text text.content over 2000 chars
# ("length should be ≤ 2000"). Chunk under that with margin so a briefing
# line of any length still writes cleanly.
TEXT_LIMIT = 1900


def rich_text(text: str) -> list:
    """Build a rich_text array for one block, chunked to ≤TEXT_LIMIT each.

    Notion allows up to 100 rich_text objects per block, so this handles
    lines up to ~190k chars — far past anything the agents produce.
    """
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    return [
        {"type": "text", "text": {"content": text[i:i + TEXT_LIMIT]}}
        for i in range(0, len(text), TEXT_LIMIT)
    ]


def build_blocks(content: str) -> list:
    """Convert markdown-ish briefing content into Notion child blocks."""
    blocks = []
    for line in content.split("\n"):
        if not line.strip():
            continue
        if line.startswith("# "):
            blocks.append({"object": "block", "type": "heading_1",
                           "heading_1": {"rich_text": rich_text(line[2:])}})
        elif line.startswith("## "):
            blocks.append({"object": "block", "type": "heading_2",
                           "heading_2": {"rich_text": rich_text(line[3:])}})
        elif line.startswith("- "):
            blocks.append({"object": "block", "type": "bulleted_list_item",
                           "bulleted_list_item": {"rich_text": rich_text(line[2:])}})
        else:
            blocks.append({"object": "block", "type": "paragraph",
                           "paragraph": {"rich_text": rich_text(line)}})
    return blocks
