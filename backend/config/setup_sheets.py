"""
config/setup_sheets.py
Run this ONCE to create your job application tracker in Google Sheets.
Usage: python config/setup_sheets.py
"""
import os
from dotenv import load_dotenv
from googleapiclient.discovery import build
from google.oauth2 import service_account

load_dotenv()

def create_job_tracker():
    creds = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_CREDENTIALS_JSON"),
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )

    sheets_service = build("sheets", "v4", credentials=creds)
    drive_service  = build("drive",  "v3", credentials=creds)

    # Create the spreadsheet
    spreadsheet = sheets_service.spreadsheets().create(body={
        "properties": {"title": "Career OS — Job Application Tracker"},
        "sheets": [{"properties": {"title": "Applications"}}]
    }).execute()

    sheet_id = spreadsheet["spreadsheetId"]
    print(f"✅ Spreadsheet created: {sheet_id}")

    # Add header row
    sheets_service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range="Applications!A1:F1",
        valueInputOption="USER_ENTERED",
        body={"values": [["Company", "Role", "URL", "Status", "Date Applied", "Notes"]]}
    ).execute()

    # Bold + freeze header row
    sheets_service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": [
            {"repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}}},
                "fields": "userEnteredFormat(textFormat,backgroundColor)"
            }},
            {"updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"
            }},
        ]}
    ).execute()

    # Share with your personal Gmail so you can actually view it
    your_email = os.getenv("GMAIL_SENDER", "")
    if your_email:
        drive_service.permissions().create(
            fileId=sheet_id,
            body={"type": "user", "role": "writer", "emailAddress": your_email},
            sendNotificationEmail=False,
        ).execute()
        print(f"   Shared with {your_email}")

    print(f"\n   Add this to your .env file:")
    print(f"   GOOGLE_SHEET_ID={sheet_id}")
    print(f"\n   View it at: https://docs.google.com/spreadsheets/d/{sheet_id}\n")
    return sheet_id

if __name__ == "__main__":
    create_job_tracker()
