"""
api/saas/schema.py
Multi-user SaaS tables. Every private table carries user_id and every query in
the SaaS routes filters by the authenticated user — data isolation is enforced
at the query layer and covered by tests.

Schema creation is idempotent (CREATE TABLE IF NOT EXISTS + additive ALTERs).
SQLite is the development store; the same DDL maps cleanly onto Postgres for
production (see docs/SAAS_MIGRATION.md).
"""


def init_saas_schema(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email_verified INTEGER NOT NULL DEFAULT 0,
            role TEXT NOT NULL DEFAULT 'user',              -- user | admin | support
            status TEXT NOT NULL DEFAULT 'trialing',        -- active|trialing|past_due|cancelled|suspended|deleted
            plan TEXT NOT NULL DEFAULT 'trial',             -- free_demo|trial|starter|pro|premium
            trial_started_at TEXT,
            trial_ends_at TEXT,
            subscription_status TEXT,                       -- stripe subscription status
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            cancelled_at TEXT,
            grace_period_ends_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS career_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            target_roles TEXT,              -- JSON array
            target_seniority TEXT,
            target_locations TEXT,          -- JSON array
            remote_preference TEXT,
            salary_target TEXT,
            industries TEXT,                -- JSON array
            companies_targeted TEXT,        -- JSON array
            companies_avoided TEXT,         -- JSON array
            current_title TEXT,
            current_skills TEXT,            -- JSON array
            desired_skills TEXT,            -- JSON array
            education TEXT,
            certifications TEXT,            -- JSON array
            resume_summary TEXT,
            linkedin_summary TEXT,
            linkedin_content TEXT,          -- pasted LinkedIn profile text (private)
            portfolio_links TEXT,           -- JSON array
            github_url TEXT,
            job_search_urgency TEXT,
            briefing_frequency TEXT,
            gmail_connection_preference TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            content TEXT NOT NULL,          -- resume text (private; never logged)
            version INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS saas_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            canonical_url TEXT,
            source TEXT,
            date_found TEXT,
            location TEXT,
            remote_type TEXT,
            salary_text TEXT,
            employment_type TEXT,
            description TEXT,
            required_skills TEXT,           -- JSON array
            preferred_skills TEXT,          -- JSON array
            validation_status TEXT NOT NULL DEFAULT 'unverified',  -- verified|unverified|expired|duplicate
            duplicate_key TEXT,
            overall_fit_score REAL,
            fit_details TEXT,               -- JSON: per-dimension scores + reasoning
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS saas_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            job_id INTEGER REFERENCES saas_jobs(id),
            status TEXT NOT NULL DEFAULT 'Found',
            application_date TEXT,
            last_event_date TEXT,
            next_follow_up_date TEXT,
            source TEXT,
            resume_version_id INTEGER,
            cover_letter_id INTEGER,
            outcome TEXT,
            outcome_reason TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS application_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            application_id INTEGER NOT NULL REFERENCES saas_applications(id),
            event_type TEXT NOT NULL,       -- status_change | gmail_event | note | assist_action
            from_status TEXT,
            to_status TEXT,
            source TEXT NOT NULL,           -- manual | gmail | automation | assist
            detail TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS skill_gaps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            skill TEXT NOT NULL,
            category TEXT,                  -- hard|tool|cloud|data|ai_ml|business|domain
            evidence TEXT,                  -- JSON: jobs it appeared in
            jobs_count INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'open',   -- open | in_progress | closed
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS teaching_moments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            skill_gap TEXT NOT NULL,
            payload TEXT NOT NULL,          -- JSON: lesson, practice_task, portfolio_task, quiz, resources...
            status TEXT NOT NULL DEFAULT 'new',    -- new | completed | dismissed
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS gmail_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            status TEXT NOT NULL DEFAULT 'disconnected',   -- connected | disconnected
            google_email TEXT,
            scopes TEXT,
            refresh_token TEXT,             -- scaffold: encrypt/KMS before real production use
            connected_at TEXT,
            disconnected_at TEXT,
            last_sync_at TEXT
        );

        CREATE TABLE IF NOT EXISTS email_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            gmail_message_id TEXT,
            thread_id TEXT,
            sender TEXT,
            subject TEXT,
            received_at TEXT,
            event_type TEXT NOT NULL,       -- application_confirmation|rejection|interview_invitation|recruiter_message|assessment|offer|follow_up_needed|unknown_career_related
            company TEXT,
            role TEXT,
            application_id INTEGER,
            confidence_score REAL,
            snippet_or_summary TEXT,        -- extracted summary only — full bodies are not stored
            action_needed TEXT,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, gmail_message_id)
        );

        CREATE TABLE IF NOT EXISTS usage_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            metric TEXT NOT NULL,           -- ai_runs | job_matches | lessons | resume_tailoring | gmail_scans | assist_requests
            period TEXT NOT NULL,           -- YYYY-MM-DD (daily buckets)
            count INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, metric, period)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            area TEXT NOT NULL,             -- job_match|skill_gap|lesson|linkedin_rec|resume_rec|job_rejected_reason|general
            target_id INTEGER,
            rating TEXT,                    -- useful | not_useful | inaccurate | other
            comment TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS assist_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            application_id INTEGER,
            job_id INTEGER,
            action TEXT NOT NULL,
            user_confirmed INTEGER NOT NULL DEFAULT 0,
            payload_summary TEXT,
            result TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS billing_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stripe_event_id TEXT UNIQUE,
            type TEXT,
            payload_summary TEXT,
            processed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_saas_jobs_user ON saas_jobs(user_id);
        CREATE INDEX IF NOT EXISTS idx_saas_apps_user ON saas_applications(user_id);
        CREATE INDEX IF NOT EXISTS idx_app_events_user ON application_events(user_id, application_id);
        CREATE INDEX IF NOT EXISTS idx_email_events_user ON email_events(user_id);
        CREATE INDEX IF NOT EXISTS idx_skill_gaps_user ON skill_gaps(user_id);
        CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_records(user_id, metric, period);
    """)
