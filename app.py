"""
VendorIQ — Smart Vendor Proposal Comparison
Main Streamlit entry point.

Run with:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="VendorIQ",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="expanded",
)

from auth.google_oauth import require_login, logout
from frontend.styles import inject_css, sidebar_user
from frontend import user_dashboard, admin_dashboard
from database.db_manager import create_tables

# Ensure DB is ready
create_tables()

# Inject shared CSS
inject_css()

# ── Auth gate ─────────────────────────────────────────────────────────────────
user = require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:#e8d5a3;padding:20px 16px 4px;letter-spacing:-0.5px;">
        ⚖ VendorIQ
    </div>
    <div style="font-size:0.7rem;color:#6b7280;padding:0 16px 16px;letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid #1e2330;">
        Vendor Intelligence Platform
    </div>
    """, unsafe_allow_html=True)

    sidebar_user(user)

    st.markdown('<div class="section-label" style="padding:0 0 4px;">Navigation</div>', unsafe_allow_html=True)

    page = st.radio(
        "",
        options=["📊 Dashboard", "⚙ Admin Panel"] if user["is_admin"] else ["📊 Dashboard"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    if st.button("Sign out", key="signout"):
        logout()

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    user_dashboard.render()

elif page == "⚙ Admin Panel":
    if not user["is_admin"]:
        st.error("Access denied. Admin only.")
    else:
        admin_dashboard.render()