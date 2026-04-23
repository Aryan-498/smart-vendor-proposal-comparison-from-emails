"""
Google OAuth2 login for Streamlit.

Fixes:
- Session persists across F5 refresh using localStorage
- Sign in button navigates in same tab (no new tab)
"""

import json
import urllib.parse
import requests
import streamlit as st
import streamlit.components.v1 as components

from config.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    ADMIN_EMAIL,
)

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_URL  = "https://www.googleapis.com/oauth2/v3/userinfo"
SCOPES           = "openid email profile"
SESSION_KEY      = "vendoriq_user_v1"   # localStorage key


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


def _save_to_localstorage(user: dict):
    """
    Persist user dict to browser localStorage so it survives F5 refresh.
    Uses a hidden iframe component to run JS.
    """
    payload = json.dumps(user).replace("'", "\\'")
    components.html(f"""
    <script>
        try {{
            localStorage.setItem('{SESSION_KEY}', JSON.stringify({json.dumps(user)}));
        }} catch(e) {{}}
    </script>
    """, height=0)


def _clear_localstorage():
    """Remove persisted session from localStorage on logout."""
    components.html(f"""
    <script>
        try {{
            localStorage.removeItem('{SESSION_KEY}');
        }} catch(e) {{}}
    </script>
    """, height=0)


def _try_restore_from_localstorage():
    """
    On page load, check localStorage for a saved session.
    If found, restore it to st.session_state without re-authenticating.
    Uses a query param trick: JS sets ?restore=<json> then Streamlit reads it.
    """
    if st.session_state.get("user"):
        return  # already logged in

    if st.session_state.get("_ls_checked"):
        return  # already attempted restore this session

    st.session_state["_ls_checked"] = True

    # Check if restore param came back from JS
    params = st.query_params
    if "restore" in params:
        try:
            user_data = json.loads(urllib.parse.unquote(params["restore"]))
            if user_data.get("email"):
                st.session_state["user"] = user_data
                st.query_params.clear()
                st.rerun()
        except Exception:
            st.query_params.clear()
        return

    # Inject JS to read localStorage and redirect back with restore param
    components.html(f"""
    <script>
        try {{
            var stored = localStorage.getItem('{SESSION_KEY}');
            if (stored) {{
                var user = JSON.parse(stored);
                if (user && user.email) {{
                    var encoded = encodeURIComponent(stored);
                    // Navigate parent window (Streamlit app) with restore param
                    window.parent.location.href = window.parent.location.pathname +
                        '?restore=' + encoded;
                }}
            }}
        }} catch(e) {{}}
    </script>
    """, height=0)


def handle_oauth_callback():
    """Handle Google's ?code= redirect."""

    if st.session_state.get("user"):
        if "code" in st.query_params:
            st.query_params.clear()
        return

    params = st.query_params

    if "code" not in params:
        return

    code = params["code"]
    st.query_params.clear()

    with st.spinner("Signing you in..."):
        try:
            tokens    = exchange_code_for_token(code)
            user_info = get_user_info(tokens["access_token"])
            email     = user_info.get("email", "")

            user = {
                "email":    email,
                "name":     user_info.get("name", email),
                "picture":  user_info.get("picture", ""),
                "is_admin": email.lower() == ADMIN_EMAIL.lower(),
            }

            st.session_state["user"] = user
            st.session_state["_ls_checked"] = True

            # Persist to localStorage for F5 survival
            _save_to_localstorage(user)

            st.rerun()

        except requests.HTTPError as e:
            st.error(f"Login failed (HTTP {e.response.status_code}). "
                     f"Check your GOOGLE_CLIENT_ID and SECRET in secrets.")
        except Exception as e:
            st.error(f"Login error: {e}")


def logout():
    st.session_state.pop("user", None)
    st.session_state.pop("_ls_checked", None)
    _clear_localstorage()
    st.rerun()


def current_user() -> dict | None:
    return st.session_state.get("user")


def require_login():
    """
    Main auth gate. Call at top of app.py.
    Order:
      1. Try restore from localStorage (F5 case)
      2. Handle OAuth callback (?code=)
      3. Show login page if still not authenticated
    """
    _try_restore_from_localstorage()
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
        font-family: 'DM Sans', sans-serif; font-size: 1rem; color: #6b7280;
        margin-bottom: 48px; letter-spacing: 0.05em; text-transform: uppercase;
    }
    .login-card {
        background: #161a24; border: 1px solid #2a2f3e; border-radius: 16px;
        padding: 40px 52px; text-align: center; max-width: 400px; width: 100%;
    }
    .login-title {
        font-family: 'DM Serif Display', serif; font-size: 1.6rem;
        color: #f0ead6; margin-bottom: 8px;
    }
    .login-desc {
        font-family: 'DM Sans', sans-serif; color: #6b7280;
        font-size: 0.9rem; margin-bottom: 0; line-height: 1.6;
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

    _, col, _ = st.columns([1, 2, 1])
    with col:
        auth_url = get_auth_url()

        # FIX: use window.parent.location.href so it stays in the SAME tab
        # instead of <a href> which some browsers open in a new tab
        components.html(f"""
        <style>
        .signin-btn {{
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
            cursor: pointer;
            border: none;
            width: 100%;
            margin-top: -100px;
        }}
        .signin-btn:hover {{ opacity: 0.85; }}
        </style>
        <button class="signin-btn"
            onclick="window.parent.location.href='{auth_url}'">
            🔐 &nbsp; Sign in with Google
        </button>
        """, height=60)