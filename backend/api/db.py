import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.getenv("CAREER_OS_DB", os.path.join(os.path.dirname(__file__), "..", "career_os.db"))


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                trigger TEXT NOT NULL DEFAULT 'manual'
            );

            CREATE TABLE IF NOT EXISTS briefings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER REFERENCES runs(id),
                date TEXT UNIQUE NOT NULL,
                content_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                jobs_applied INTEGER DEFAULT 0,
                skills_gap_count INTEGER DEFAULT 0,
                interview_score REAL DEFAULT 0,
                portfolio_items INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS interview_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                category TEXT NOT NULL,
                question TEXT NOT NULL,
                user_answer TEXT,
                ai_feedback TEXT,
                score REAL
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_applied TEXT NOT NULL,
                company TEXT NOT NULL,
                role TEXT NOT NULL,
                url TEXT,
                status TEXT NOT NULL DEFAULT 'Applied',
                notes TEXT,
                blob_url TEXT,
                last_updated TEXT
            );
        """)
