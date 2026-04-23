"""
Robust Google OAuth2 for Streamlit.
Handles the redirect callback even after Streamlit reloads.
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
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(GOOGLE_USER_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def handle_oauth_callback():
    """
    Must be called at the very top of app.py before any st.stop().
    Reads ?code= from the URL, exchanges it for a token, stores user in session.
    """

    # Already logged in — just clear leftover params
    if st.session_state.get("user"):
        if "code" in st.query_params:
            st.query_params.clear()
        return

    params = st.query_params

    if "code" not in params:
        return

    code = params["code"]

    # Clear the URL immediately so a refresh doesn't re-submit the code
    st.query_params.clear()

    with st.spinner("Signing you in..."):
        try:
            tokens    = exchange_code_for_token(code)
            user_info = get_user_info(tokens["access_token"])
            email     = user_info.get("email", "")

            st.session_state["user"] = {
                "email":    email,
                "name":     user_info.get("name", email),
                "picture":  user_info.get("picture", ""),
                "is_admin": email.lower() == ADMIN_EMAIL.lower(),
            }

            st.rerun()

        except requests.HTTPError as e:
            st.error(f"Google login failed (HTTP {e.response.status_code}). "
                     f"Check your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in secrets.toml.")
        except Exception as e:
            st.error(f"Login error: {e}")


def logout():
    st.session_state.pop("user", None)
    st.rerun()


def current_user() -> dict | None:
    return st.session_state.get("user")


def require_login():
    """Call this at the top of app.py. Returns user dict or stops the page."""
    handle_oauth_callback()
    user = current_user()
    if not user:
        _render_login_page()
        st.stop()
    return user


def _render_login_page():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500&display=swap');
    [data-testid="stAppViewContainer"] { background: #0d0f14; }
    .login-wrap {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 75vh; gap: 0;
    }
    .login-logo {
        font-family: 'DM Serif Display', serif; font-size: 3rem;
        color: #e8d5a3; letter-spacing: -1px; margin-bottom: 6px;
    }
    .login-sub {
        font-family: 'DM Sans', sans-serif; font-size: 1rem;
        color: #6b7280; margin-bottom: 48px; letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .login-card {
        background: #161a24; border: 1px solid #2a2f3e;
        border-radius: 16px; padding: 40px 52px;
        text-align: center; max-width: 400px; width: 100%;
    }
    .login-title {
        font-family: 'DM Serif Display', serif; font-size: 1.6rem;
        color: #f0ead6; margin-bottom: 8px;
    }
    .login-desc {
        font-family: 'DM Sans', sans-serif; color: #6b7280;
        font-size: 0.9rem; margin-bottom: 0px; line-height: 1.6;
    }
    </style>
    <div class="login-wrap">
        <div class="login-logo">⚖ VendorIQ</div>
        <div class="login-sub">Smart Vendor Proposal Comparison</div>
        <div class="login-card">
            <div class="login-title">Welcome back</div>
            <div class="login-desc">Sign in with your Google account to continue.</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Render the button below the card using Streamlit columns
    _, col, _ = st.columns([1, 2, 1])
    with col:
        auth_url = get_auth_url()
        st.markdown(f"""
        <div style="margin-top:-80px;">
        <a href="{auth_url}" style="
            display:block; background:#e8d5a3; color:#0d0f14;
            font-family:'DM Sans',sans-serif; font-weight:500;
            text-align:center; padding:14px 24px; border-radius:8px;
            text-decoration:none; font-size:0.95rem;">
            🔐 &nbsp; Sign in with Google
        </a>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:16px;font-size:0.75rem;color:#6b7280;text-align:center;font-family:'DM Sans',sans-serif;">
            After signing in, if you see a blank page,<br>
            go back to <b>localhost:8501</b> manually.
        </div>
        """, unsafe_allow_html=True)