"""
tools/google_creds.py
Loads a Google service-account credentials file written from a GitHub Actions
secret via `echo '${{ secrets.GOOGLE_CREDENTIALS_JSON }}' > ...`. That secret
is sometimes copy-pasted from a Windows editor and carries a UTF-8 BOM, which
google-auth's from_service_account_file() chokes on (it opens without
utf-8-sig). Reading it ourselves with utf-8-sig and handing google-auth the
parsed dict via from_service_account_info() sidesteps the issue for good,
regardless of what the upstream secret contains.
"""
import json

from google.oauth2 import service_account


def load_google_credentials(path: str, scopes: list[str]) -> service_account.Credentials:
    with open(path, encoding="utf-8-sig") as f:
        info = json.load(f)
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)
