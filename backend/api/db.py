import sqlite3
import os
from contextlib import contextmanager

from api import config


def get_connection():
    path = config.db_path()
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path)
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


def _add_column_if_missing(conn, table: str, column: str, ddl: str):
    """Idempotent, non-destructive schema migration for existing databases."""
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


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
                status TEXT NOT NULL DEFAULT 'Found',
                notes TEXT,
                blob_url TEXT,
                last_updated TEXT
            );
        """)
        # Additive migrations for databases created before these columns existed.
        _add_column_if_missing(conn, "runs", "error_message", "TEXT")
        _add_column_if_missing(conn, "runs", "stage", "TEXT")
        _add_column_if_missing(conn, "runs", "user_id", "INTEGER")
        _add_column_if_missing(conn, "applications", "source", "TEXT")
        _add_column_if_missing(conn, "applications", "validation_status", "TEXT")

        # Multi-user SaaS tables (all keyed by user_id).
        from api.saas.schema import init_saas_schema
        init_saas_schema(conn)
