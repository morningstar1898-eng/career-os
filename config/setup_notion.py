"""
config/setup_notion.py
Run this ONCE to create the Notion database your agents will write to.
Usage: python config/setup_notion.py
"""
import os
from dotenv import load_dotenv
from notion_client import Client

load_dotenv()

def create_notion_database():
    notion = Client(auth=os.getenv("NOTION_API_KEY"))

    # You need a Notion page to put the database in.
    # Get the page ID from the URL of any Notion page you own:
    # notion.so/yourworkspace/[THIS-IS-THE-PAGE-ID]
    parent_page_id = input("Paste your Notion parent page ID (from the URL): ").strip()

    print("Creating Career OS database in Notion...")

    db = notion.databases.create(
        parent={"type": "page_id", "page_id": parent_page_id},
        title=[{"type": "text", "text": {"content": "Career OS Daily Briefings"}}],
        properties={
            "Name": {"title": {}},
            "Date": {"date": {}},
            "Skills Gap": {"rich_text": {}},
            "Jobs Applied": {"number": {}},
            "Lesson Topic": {"rich_text": {}},
            "Portfolio Update": {"url": {}},
            "Status": {
                "select": {
                    "options": [
                        {"name": "Pending",   "color": "gray"},
                        {"name": "Completed", "color": "green"},
                        {"name": "Error",     "color": "red"},
                    ]
                }
            },
        },
    )

    db_id = db["id"]
    print(f"\n✅ Database created!")
    print(f"   Database ID: {db_id}")
    print(f"\n   Add this to your .env file:")
    print(f"   NOTION_DATABASE_ID={db_id}\n")
    return db_id

if __name__ == "__main__":
    create_notion_database()
