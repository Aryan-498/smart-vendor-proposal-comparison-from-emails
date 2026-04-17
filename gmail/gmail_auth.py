import os
import json
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from config.settings import GMAIL_SCOPES

TOKEN_PATH       = "config/token.json"
CREDENTIALS_PATH = "config/credentials.json"


def _try_load_from_secrets(secret_key, file_path):
    """
    Try to decode a base64 secret and write it to disk.
    Works on Streamlit Cloud where files can't be committed.
    Silently skips if the secret doesn't exist.
    """
    if os.path.exists(file_path):
        return  # already on disk, nothing to do

    b64 = ""

    # Try Streamlit secrets first
    try:
        import streamlit as st
        b64 = st.secrets.get(secret_key, "")
    except Exception:
        pass

    # Fallback to environment variable
    if not b64:
        b64 = os.getenv(secret_key, "")

    if b64:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        with open(file_path, "w") as f:
            json.dump(data, f)


def authenticate_gmail():
    # Pull files from secrets if running on Streamlit Cloud
    _try_load_from_secrets("GOOGLE_CREDENTIALS_B64", CREDENTIALS_PATH)
    _try_load_from_secrets("GOOGLE_TOKEN_B64",       TOKEN_PATH)

    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token exists but expired — just refresh it silently
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        elif os.path.exists(CREDENTIALS_PATH):
            # ── LOCAL: launch browser flow ────────────────────────────────────
            flow  = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())

        else:
            # ── STREAMLIT CLOUD: no credentials file, guide the user ──────────
            raise RuntimeError(
                "Gmail credentials not found.\n\n"
                "On Streamlit Cloud:\n"
                "1. Run locally once to generate config/token.json\n"
                "2. Run: cat config/credentials.json | base64\n"
                "   Add output as GOOGLE_CREDENTIALS_B64 in Streamlit secrets\n"
                "3. Run: cat config/token.json | base64\n"
                "   Add output as GOOGLE_TOKEN_B64 in Streamlit secrets"
            )

    return creds