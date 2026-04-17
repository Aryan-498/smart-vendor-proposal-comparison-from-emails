"""
Google OAuth2 login for the Streamlit website.

Flow:
1. User clicks "Sign in with Google"
2. We redirect them to Google's auth page
3. Google redirects back with ?code=...
4. We exchange the code for an access token
5. We fetch their profile (email, name, picture)
6. We store the session in st.session_state
"""

import urllib.parse
import requests
import streamlit as st

from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    ADMIN_EMAIL,
)

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = "openid email profile"


def get_auth_url() -> str:
    """Build the Google OAuth2 authorization URL."""

    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "select_account",
    }

    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_token(code: str) -> dict:
    """Exchange the auth code for an access + id token."""

    data = {
        "code":          code,
        "client_id":     GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri":  GOOGLE_REDIRECT_URI,
        "grant_type":    "authorization_code",
    }

    resp = requests.post(GOOGLE_TOKEN_URL, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_user_info(access_token: str) -> dict:
    """Fetch the user's profile from Google."""

    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(GOOGLE_USER_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def handle_oauth_callback():
    """
    Called on every Streamlit page load.
    If the URL contains ?code=..., complete the OAuth flow and store user in session.
    """

    params = st.query_params

    if "code" not in params:
        return

    if st.session_state.get("user"):
        # Already logged in — clear the URL param cleanly
        st.query_params.clear()
        return

    code = params["code"]

    try:
        tokens    = exchange_code_for_token(code)
        user_info = get_user_info(tokens["access_token"])

        email = user_info.get("email", "")

        st.session_state["user"] = {
            "email":   email,
            "name":    user_info.get("name", email),
            "picture": user_info.get("picture", ""),
            "is_admin": email.lower() == ADMIN_EMAIL.lower(),
        }

    except Exception as e:
        st.error(f"Login failed: {e}")

    finally:
        st.query_params.clear()


def logout():
    st.session_state.pop("user", None)
    st.rerun()


def current_user() -> dict | None:
    return st.session_state.get("user")


def require_login():
    """Show login page if not authenticated. Returns user dict if logged in."""

    handle_oauth_callback()
    user = current_user()

    if not user:
        _render_login_page()
        st.stop()

    return user


def _render_login_page():
    """Render a clean, branded login screen."""

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');

    [data-testid="stAppViewContainer"] {
        background: #0d0f14;
    }
    .login-wrap {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 80vh;
        gap: 0;
    }
    .login-logo {
        font-family: 'DM Serif Display', serif;
        font-size: 3rem;
        color: #e8d5a3;
        letter-spacing: -1px;
        margin-bottom: 6px;
    }
    .login-sub {
        font-family: 'DM Sans', sans-serif;
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 48px;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .login-card {
        background: #161a24;
        border: 1px solid #2a2f3e;
        border-radius: 16px;
        padding: 48px 56px;
        text-align: center;
        max-width: 400px;
        width: 100%;
    }
    .login-title {
        font-family: 'DM Serif Display', serif;
        font-size: 1.6rem;
        color: #f0ead6;
        margin-bottom: 8px;
    }
    .login-desc {
        font-family: 'DM Sans', sans-serif;
        color: #6b7280;
        font-size: 0.9rem;
        margin-bottom: 32px;
        line-height: 1.6;
    }
    </style>
    <div class="login-wrap">
        <div class="login-logo">⚖ VendorIQ</div>
        <div class="login-sub">Smart Vendor Proposal Comparison</div>
        <div class="login-card">
            <div class="login-title">Welcome back</div>
            <div class="login-desc">Sign in with your Google account to access the dashboard. Admin accounts have additional privileges.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_url = get_auth_url()
        st.markdown(f"""
        <a href="{auth_url}" style="
            display: block;
            background: #e8d5a3;
            color: #0d0f14;
            font-family: 'DM Sans', sans-serif;
            font-weight: 500;
            text-align: center;
            padding: 14px 24px;
            border-radius: 8px;
            text-decoration: none;
            font-size: 0.95rem;
            margin-top: -120px;
        ">
            🔐 &nbsp; Sign in with Google
        </a>
        """, unsafe_allow_html=True)