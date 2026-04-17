import os
import json
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from config.settings import GMAIL_SCOPES

TOKEN_PATH       = "config/token.json"
CREDENTIALS_PATH = "config/credentials.json"


def _ensure_credentials_file():
    """
    On Streamlit Cloud, credentials.json can't be committed to git.
    Instead, store it as a base64 string in secrets: GOOGLE_CREDENTIALS_B64
    This function decodes it and writes it to disk if needed.
    """
    if os.path.exists(CREDENTIALS_PATH):
        return

    try:
        import streamlit as st
        b64 = st.secrets.get("GOOGLE_CREDENTIALS_B64", "")
    except Exception:
        b64 = os.getenv("GOOGLE_CREDENTIALS_B64", "")

    if b64:
        os.makedirs("config", exist_ok=True)
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        with open(CREDENTIALS_PATH, "w") as f:
            json.dump(data, f)


def _ensure_token_file():
    """
    Same pattern for token.json — stored as GOOGLE_TOKEN_B64 in secrets.
    """
    if os.path.exists(TOKEN_PATH):
        return

    try:
        import streamlit as st
        b64 = st.secrets.get("GOOGLE_TOKEN_B64", "")
    except Exception:
        b64 = os.getenv("GOOGLE_TOKEN_B64", "")

    if b64:
        os.makedirs("config", exist_ok=True)
        data = json.loads(base64.b64decode(b64).decode("utf-8"))
        with open(TOKEN_PATH, "w") as f:
            json.dump(data, f)


def authenticate_gmail():
    _ensure_credentials_file()
    _ensure_token_file()

    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as token:
                token.write(creds.to_json())
        else:
            raise RuntimeError(
                "Gmail token missing or expired. "
                "Run locally first to generate token.json, then add "
                "GOOGLE_TOKEN_B64 to your Streamlit secrets."
            )

    return creds