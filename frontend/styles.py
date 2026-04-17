GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

/* ── Base ── */
[data-testid="stAppViewContainer"] { background: #0d0f14; }
[data-testid="stSidebar"]          { background: #0f1219; border-right: 1px solid #1e2330; }
[data-testid="stHeader"]           { background: transparent; }

html, body, .stApp {
    font-family: 'DM Sans', sans-serif;
    color: #c9d1e0;
}

/* ── Typography ── */
h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
    color: #e8d5a3;
    letter-spacing: -0.5px;
}
h1 { font-size: 2.2rem; margin-bottom: 4px; }
h2 { font-size: 1.5rem; margin-bottom: 2px; }
h3 { font-size: 1.1rem; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: #161a24;
    border: 1px solid #2a2f3e;
    border-radius: 12px;
    padding: 20px 24px;
}
[data-testid="stMetricLabel"]  { color: #6b7280 !important; font-size: 0.8rem !important; letter-spacing: 0.06em; text-transform: uppercase; }
[data-testid="stMetricValue"]  { color: #e8d5a3 !important; font-family: 'DM Serif Display', serif !important; font-size: 2rem !important; }
[data-testid="stMetricDelta"]  { font-size: 0.8rem !important; }

/* ── Dataframe / tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid #2a2f3e;
    border-radius: 10px;
    overflow: hidden;
}

/* ── Buttons ── */
.stButton > button {
    background: #e8d5a3;
    color: #0d0f14;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    border: none;
    border-radius: 8px;
    padding: 10px 22px;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.85; }

/* Danger button */
.stButton.danger > button {
    background: #c0392b;
    color: #fff;
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] select {
    background: #161a24 !important;
    border: 1px solid #2a2f3e !important;
    color: #c9d1e0 !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid #2a2f3e;
    gap: 8px;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'DM Sans', sans-serif;
    color: #6b7280;
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #e8d5a3;
    border-bottom: 2px solid #e8d5a3;
    background: transparent;
}

/* ── Sidebar nav ── */
.sidebar-user {
    padding: 20px 16px 12px;
    border-bottom: 1px solid #1e2330;
    margin-bottom: 8px;
}
.sidebar-user img {
    width: 38px;
    height: 38px;
    border-radius: 50%;
    border: 2px solid #e8d5a3;
}
.sidebar-user .user-name {
    font-family: 'DM Serif Display', serif;
    color: #e8d5a3;
    font-size: 1rem;
    margin-top: 6px;
}
.sidebar-user .user-email {
    color: #6b7280;
    font-size: 0.75rem;
}
.admin-badge {
    display: inline-block;
    background: #e8d5a3;
    color: #0d0f14;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 20px;
    margin-top: 4px;
}

/* ── Section dividers ── */
.section-label {
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6b7280;
    margin: 24px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid #1e2330;
}

/* ── Alerts ── */
.info-box {
    background: #161a24;
    border: 1px solid #2a2f3e;
    border-left: 3px solid #e8d5a3;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #c9d1e0;
    margin: 12px 0;
}
.success-box {
    background: #0f1f18;
    border: 1px solid #1a3a27;
    border-left: 3px solid #34d399;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #a7f3d0;
    margin: 12px 0;
}
.danger-box {
    background: #1f0f0f;
    border: 1px solid #3a1a1a;
    border-left: 3px solid #f87171;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: #fca5a5;
    margin: 12px 0;
}

/* ── Score badge ── */
.score-pill {
    display: inline-block;
    background: #e8d5a3;
    color: #0d0f14;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
}
</style>
"""


def inject_css():
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def sidebar_user(user: dict):
    import streamlit as st
    pic = user.get("picture", "")
    name = user.get("name", "User")
    email = user.get("email", "")
    is_admin = user.get("is_admin", False)

    img_tag = f'<img src="{pic}" />' if pic else ""
    badge   = '<div class="admin-badge">Admin</div>' if is_admin else ""

    st.sidebar.markdown(f"""
    <div class="sidebar-user">
        {img_tag}
        <div class="user-name">{name}</div>
        <div class="user-email">{email}</div>
        {badge}
    </div>
    """, unsafe_allow_html=True)