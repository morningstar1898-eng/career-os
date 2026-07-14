"""
tools/shared_tools.py
Custom tools that agents can call — web search, Notion, Sheets, Azure.
"""
import os, json, requests
from datetime import datetime
from crewai.tools import BaseTool
from notion_client import Client as NotionClient
from tools.notion_blocks import build_blocks, TEXT_LIMIT
from googleapiclient.discovery import build
from tools.google_creds import load_google_credentials

# ─────────────────────────────────────────────
# 1. Web Search Tool (Serper)
# ─────────────────────────────────────────────
class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = "Search the web for current information. Input: search query string."

    def _run(self, query: str) -> str:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": os.getenv("SERPER_API_KEY"), "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        data = r.json()
        results = []
        for item in data.get("organic", [])[:5]:
            results.append(f"- {item['title']}: {item.get('snippet','')}\n  URL: {item['link']}")
        return "\n".join(results) if results else "No results found."


# ─────────────────────────────────────────────
# 2. Notion Writer Tool
# ─────────────────────────────────────────────
class NotionWriterTool(BaseTool):
    name: str = "write_to_notion"
    description: str = "Write content to a Notion page. Input: JSON with keys 'title' and 'content' (markdown string)."

    def _run(self, input_str: str) -> str:
        try:
            data = json.loads(input_str)
            title = data.get("title", f"Briefing {datetime.now().strftime('%Y-%m-%d')}")
            content = data.get("content", "")
        except Exception:
            title = f"Briefing {datetime.now().strftime('%Y-%m-%d')}"
            content = input_str

        notion = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        db_id = os.getenv("NOTION_DATABASE_ID")

        # Split content into blocks; rich_text is chunked to stay under
        # Notion's 2000-char-per-text-object limit (a 14k-char line from the
        # orchestrator killed every write on 2026-07-09).
        blocks = build_blocks(content)

        # Notion caps children at 100 blocks per request — create the page with
        # the first chunk, then append the rest in chunks of 100 so long
        # briefings are never silently truncated.
        page = notion.pages.create(
            parent={"database_id": db_id},
            properties={"Name": {"title": [{"text": {"content": title[:TEXT_LIMIT]}}]}},
            children=blocks[:100],
        )
        appended = min(len(blocks), 100)
        failed_chunks = 0
        for i in range(100, len(blocks), 100):
            try:
                notion.blocks.children.append(block_id=page["id"], children=blocks[i:i + 100])
                appended += len(blocks[i:i + 100])
            except Exception:
                failed_chunks += 1
        if failed_chunks:
            return (
                f"⚠️ Written to Notion: '{title}' but {failed_chunks} chunk(s) failed to append "
                f"({appended}/{len(blocks)} blocks saved). Content may be incomplete."
            )
        return f"✅ Written to Notion: '{title}' ({appended} blocks)"


# ─────────────────────────────────────────────
# 3. Google Sheets Logger Tool
# ─────────────────────────────────────────────
class SheetsLoggerTool(BaseTool):
    name: str = "log_to_sheets"
    description: str = (
        "Log job opportunities to the Google Sheets tracker. Input is JSON and can be EITHER "
        "a single object OR an array of objects (preferred — log many at once in one call). "
        "Each object has keys: company, role, url, status, date_applied, notes. "
        "Status must be 'Found', 'Drafted', or 'Ready to Apply' — never 'Applied': "
        "this system drafts materials but does NOT submit applications; only the user "
        "marks a job Applied after submitting it manually."
    )

    def _run(self, input_str: str) -> str:
        # Strip UTF-8 BOM, whitespace, and any markdown code fences the model
        # may wrap around the JSON (these were silently breaking every log).
        raw = (input_str or "").lstrip("﻿").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw[:4].lower() == "json":
                raw = raw[4:].strip()
        try:
            data = json.loads(raw)
        except Exception:
            return "Error: input must be valid JSON."

        creds = load_google_credentials(
            os.getenv("GOOGLE_CREDENTIALS_JSON"),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        values = service.spreadsheets().values()

        # One-time: ensure a header row so the running application log reads
        # like a proper reference table. Never let this block the actual log.
        header = ["Company", "Role", "URL", "Status", "Date Applied", "Notes"]
        try:
            first = values.get(
                spreadsheetId=sheet_id, range="Sheet1!A1:F1"
            ).execute().get("values", [])
            first_row = first[0] if first else []
            if not first_row or first_row[0] != header[0]:
                if first_row:  # existing data with no header → push a blank row on top
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={"requests": [{"insertDimension": {
                            "range": {"sheetId": 0, "dimension": "ROWS",
                                      "startIndex": 0, "endIndex": 1},
                            "inheritFromBefore": False}}]},
                    ).execute()
                values.update(
                    spreadsheetId=sheet_id, range="Sheet1!A1:F1",
                    valueInputOption="USER_ENTERED", body={"values": [header]},
                ).execute()
        except Exception:
            pass  # header is cosmetic; proceed to log regardless

        today = datetime.now().strftime("%Y-%m-%d")
        # Automation may only log these statuses. 'Applied' is reserved for a
        # manual user action — anything else is coerced to 'Found'.
        automation_statuses = {"Found", "Drafted", "Ready to Apply"}
        items = data if isinstance(data, list) else [data]
        rows = []
        for d in items:
            if not isinstance(d, dict):
                continue
            status = d.get("status", "Found")
            if status not in automation_statuses:
                status = "Found"
            rows.append([
                d.get("company", ""),
                d.get("role", ""),
                d.get("url", ""),
                status,
                d.get("date_applied", today),
                d.get("notes", ""),
            ])
        if not rows:
            return "Error: no valid application objects to log."
        values.append(
            spreadsheetId=sheet_id,
            range="Sheet1!A:F",
            valueInputOption="USER_ENTERED",
            body={"values": rows}
        ).execute()
        return f"✅ Logged {len(rows)} application(s) to Sheets"


# ─────────────────────────────────────────────
# 4. Google Sheets Reader Tool
# ─────────────────────────────────────────────
class SheetsReaderTool(BaseTool):
    name: str = "read_from_sheets"
    description: str = (
        "Read all job applications from the Google Sheets tracker. "
        "Returns a JSON array of all logged applications with their current status, "
        "company, role, URL, date_applied, and notes. No input required."
    )

    def _run(self, query: str = "") -> str:
        creds = load_google_credentials(
            os.getenv("GOOGLE_CREDENTIALS_JSON"),
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        service = build("sheets", "v4", credentials=creds)
        result = service.spreadsheets().values().get(
            spreadsheetId=os.getenv("GOOGLE_SHEET_ID"),
            range="Sheet1!A:F"
        ).execute()
        values = result.get("values", [])
        if not values or len(values) < 2:
            return json.dumps([])
        headers = [h.lower().replace(" ", "_") for h in values[0]]
        applications = []
        for row in values[1:]:
            obj = {headers[i]: (row[i] if i < len(row) else "") for i in range(len(headers))}
            applications.append(obj)
        return json.dumps(applications)


# ─────────────────────────────────────────────
# 5. Application Materials Save Tool
# ─────────────────────────────────────────────
class SaveMaterialsTool(BaseTool):
    name: str = "save_application_materials"
    description: str = (
        "Save cover letter + resume bullets to Azure Blob Storage for future reference. "
        "Input: JSON with keys 'company' (string), 'role' (string), 'materials' (full text of "
        "the generated cover letter and bullets). Returns the blob URL."
    )

    def _run(self, input_str: str) -> str:
        from azure.storage.blob import BlobServiceClient
        raw = (input_str or "").lstrip("﻿").strip()
        if raw.startswith("```"):
            raw = raw.strip("`").strip()
            if raw[:4].lower() == "json":
                raw = raw[4:].strip()
        try:
            data = json.loads(raw)
            company = data.get("company", "unknown").lower().replace(" ", "-").replace("/", "-")
            role = data.get("role", "unknown").lower().replace(" ", "-").replace("/", "-")[:50]
            materials = data.get("materials", "")
        except Exception:
            return "Error: input must be JSON with company, role, materials."

        date_str = datetime.now().strftime("%Y-%m-%d")
        blob_name = f"application-materials/{date_str}/{company}--{role}.txt"

        conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not conn_str:
            return "Error: AZURE_STORAGE_CONNECTION_STRING not set."

        client = BlobServiceClient.from_connection_string(conn_str)
        container = os.getenv("AZURE_STORAGE_CONTAINER", "portfolio-charts")
        try:
            client.get_blob_client(container=container, blob=blob_name).upload_blob(
                materials.encode("utf-8"), overwrite=True
            )
            return f"✅ Materials saved: {container}/{blob_name}"
        except Exception as e:
            return f"Error saving materials: {str(e)[:200]}"


# ─────────────────────────────────────────────
# 6. Azure Blob Upload Tool
# ─────────────────────────────────────────────
class AzureBlobTool(BaseTool):
    name: str = "upload_to_azure"
    description: str = "Upload a local file to Azure Blob Storage. Input: local file path string."

    def _run(self, file_path: str) -> str:
        from azure.storage.blob import BlobServiceClient
        client = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
        container = os.getenv("AZURE_STORAGE_CONTAINER", "portfolio-charts")
        blob_name = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            client.get_blob_client(container=container, blob=blob_name).upload_blob(f, overwrite=True)
        account = client.account_name
        return f"✅ Uploaded: https://{account}.blob.core.windows.net/{container}/{blob_name}"
