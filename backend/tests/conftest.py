"""
Test configuration. Environment is set BEFORE the app is imported so the
test database and test credentials are picked up. No real integrations
(Anthropic, Notion, Sheets, SMTP) are needed — these tests cover the API
surface: auth, status rules, ingest validation.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["CAREER_OS_API_TOKEN"] = "test-token"
os.environ["CAREER_OS_PASSWORD"] = "test-pass"
os.environ["INGEST_SECRET"] = "test-ingest"
os.environ["AUTH_SECRET"] = "test-auth-secret-for-jwt-signing"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["TRIAL_DAYS"] = "3"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
os.environ["STRIPE_PRICE_PRO"] = "price_pro_test"
os.environ["ENV"] = "test"
os.environ.pop("ALLOW_MANUAL_RUNS", None)
os.environ.pop("PUBLIC_DEMO_MODE", None)

_tmp_dir = tempfile.mkdtemp(prefix="career-os-tests-")
os.environ["CAREER_OS_DB"] = os.path.join(_tmp_dir, "test_career_os.db")

import pytest
from fastapi.testclient import TestClient

from api.main import app  # noqa: E402  (env must be set first)

AUTH = {"Authorization": "Bearer test-token"}


@pytest.fixture(scope="session")
def client():
    # Context manager runs the startup event (init_db on the test database).
    with TestClient(app) as c:
        yield c
