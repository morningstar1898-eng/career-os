"""
Offline tests for the Notion block builder. Locks in the fix for the
2026-07-09 failure where a single 14k-char line from the orchestrator made
Notion reject every write ("text.content.length should be ≤ 2000, instead
was 14004"): any line, however long, must produce rich_text objects that
each stay under Notion's 2000-char limit while preserving the full content.
"""
from tools.notion_blocks import TEXT_LIMIT, build_blocks, rich_text

NOTION_HARD_LIMIT = 2000


def all_rich_text(blocks):
    return [rt for b in blocks for rt in b[b["type"]]["rich_text"]]


def joined_content(blocks):
    return "".join(rt["text"]["content"] for rt in all_rich_text(blocks))


# ── rich_text chunking ──────────────────────────────────────────────────────

def test_short_text_is_single_object():
    rt = rich_text("hello")
    assert rt == [{"type": "text", "text": {"content": "hello"}}]


def test_empty_text_yields_one_empty_object():
    assert rich_text("") == [{"type": "text", "text": {"content": ""}}]


def test_long_text_chunked_under_notion_limit():
    text = "x" * 14004  # exact length from the failed run
    rt = rich_text(text)
    assert len(rt) > 1
    assert all(len(obj["text"]["content"]) <= NOTION_HARD_LIMIT for obj in rt)
    assert "".join(obj["text"]["content"] for obj in rt) == text


def test_boundary_lengths():
    for n in (TEXT_LIMIT - 1, TEXT_LIMIT, TEXT_LIMIT + 1, NOTION_HARD_LIMIT):
        rt = rich_text("a" * n)
        assert all(len(obj["text"]["content"]) <= TEXT_LIMIT for obj in rt)
        assert sum(len(obj["text"]["content"]) for obj in rt) == n


# ── build_blocks ────────────────────────────────────────────────────────────

def test_markdown_types_preserved():
    blocks = build_blocks("# Title\n## Section\n- bullet\nplain text")
    assert [b["type"] for b in blocks] == [
        "heading_1", "heading_2", "bulleted_list_item", "paragraph"]
    assert joined_content(blocks) == "TitleSectionbulletplain text"


def test_blank_lines_skipped():
    assert build_blocks("one\n\n   \ntwo") == build_blocks("one\ntwo")


def test_14k_line_briefing_writes_as_valid_blocks():
    # Reproduces the 2026-07-09 payload shape: one enormous single-line value.
    content = "# Daily Briefing\n" + ("job details | " * 1000)
    blocks = build_blocks(content)
    assert all(
        len(rt["text"]["content"]) <= NOTION_HARD_LIMIT
        for rt in all_rich_text(blocks)
    )
    # Nothing lost in the chunking.
    assert joined_content(blocks) == "Daily Briefing" + "job details | " * 1000


def test_long_bullet_stays_a_bullet():
    blocks = build_blocks("- " + "b" * 5000)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "bulleted_list_item"
    rts = blocks[0]["bulleted_list_item"]["rich_text"]
    assert len(rts) == 3
    assert all(len(rt["text"]["content"]) <= NOTION_HARD_LIMIT for rt in rts)
