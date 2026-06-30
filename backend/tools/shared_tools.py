"""
tools/shared_tools.py
Custom tools that agents can call — web search, Notion, Sheets, Azure.
"""
import os, json, requests
from datetime import datetime
from crewai.tools import BaseTool
from notion_client import Client as NotionClient
from googleapiclient.discovery import build
from google.oauth2 import service_account

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

        # Split content into paragraph blocks
        blocks = []
        for line in content.split("\n"):
            if not line.strip():
                continue
            if line.startswith("# "):
                blocks.append({"object":"block","type":"heading_1","heading_1":{"rich_text":[{"type":"text","text":{"content":line[2:]}}]}})
            elif line.startswith("## "):
                blocks.append({"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":line[3:]}}]}})
            elif line.startswith("- "):
                blocks.append({"object":"block","type":"bulleted_list_item","bulleted_list_item":{"rich_text":[{"type":"text","text":{"content":line[2:]}}]}})
            else:
                blocks.append({"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":line}}]}})

        notion.pages.create(
            parent={"database_id": db_id},
            properties={"Name": {"title": [{"text": {"content": title}}]}},
            children=blocks[:100]  # Notion API limit per request
        )
        return f"✅ Written to Notion: '{title}'"


# ─────────────────────────────────────────────
# 3. Google Sheets Logger Tool
# ─────────────────────────────────────────────
class SheetsLoggerTool(BaseTool):
    name: str = "log_to_sheets"
    description: str = (
        "Log job applications to Google Sheets. Input is JSON and can be EITHER a single "
        "object OR an array of objects (preferred — log many at once in one call). Each "
        "object has keys: company, role, url, status, date_applied, notes."
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

        creds = service_account.Credentials.from_service_account_file(
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
        items = data if isinstance(data, list) else [data]
        rows = []
        for d in items:
            if not isinstance(d, dict):
                continue
            rows.append([
                d.get("company", ""),
                d.get("role", ""),
                d.get("url", ""),
                d.get("status", "Applied"),
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
        creds = service_account.Credentials.from_service_account_file(
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
