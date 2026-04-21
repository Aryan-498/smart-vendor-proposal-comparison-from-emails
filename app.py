import time
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

create_tables()
inject_css()

user = require_login()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="font-family:'DM Serif Display',serif;font-size:1.4rem;color:#e8d5a3;
         padding:20px 16px 4px;letter-spacing:-0.5px;">
        ⚖ VendorIQ
    </div>
    <div style="font-size:0.7rem;color:#6b7280;padding:0 16px 16px;
         letter-spacing:0.08em;text-transform:uppercase;border-bottom:1px solid #1e2330;">
        Vendor Intelligence Platform
    </div>
    """, unsafe_allow_html=True)

    sidebar_user(user)

    st.markdown('<div class="section-label" style="padding:0 0 4px;">Navigation</div>',
                unsafe_allow_html=True)

    options = ["📊 Dashboard", "⚙ Admin Panel"] if user["is_admin"] else ["📊 Dashboard"]
    page = st.radio("", options=options, label_visibility="collapsed")

    st.markdown("---")

    # ── Live refresh controls ─────────────────────────────────────────────────
    st.markdown('<div class="section-label">Live Updates</div>', unsafe_allow_html=True)

    # Manual refresh button
    if st.button("🔄 Refresh Now", key="manual_refresh", use_container_width=True):
        st.rerun()

    # Auto-refresh toggle
    auto_refresh = st.toggle("Auto-refresh", value=False, key="auto_refresh")

    if auto_refresh:
        interval = st.select_slider(
            "Interval",
            options=[15, 30, 60, 120, 300],
            value=30,
            format_func=lambda x: f"{x}s" if x < 60 else f"{x//60}m",
            key="refresh_interval"
        )
        st.markdown(
            f'<div style="font-size:0.72rem;color:#6b7280;margin-top:4px;">'
            f'Refreshing every {interval}s</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")

    if st.button("Sign out", key="signout"):
        logout()

# ── Page routing ──────────────────────────────────────────────────────────────
if page == "📊 Dashboard":
    user_dashboard.render(user)
elif page == "⚙ Admin Panel":
    if not user["is_admin"]:
        st.error("Access denied.")
    else:
        admin_dashboard.render()

# ── Auto-refresh ticker (runs at the bottom after page renders) ───────────────
if st.session_state.get("auto_refresh"):
    interval = st.session_state.get("refresh_interval", 30)
    time.sleep(interval)
    st.rerun()