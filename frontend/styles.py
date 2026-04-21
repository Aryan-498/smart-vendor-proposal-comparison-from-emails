GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

/* ── CSS variables — auto-switch dark/light ───────────────────────────────── */
:root {
    --accent:      #b8955a;
    --accent-soft: #e8d5a3;
    --muted:       #6b7280;
    --radius:      10px;
}

/* Dark mode tokens */
[data-theme="dark"], .stApp[data-theme="dark"] {
    --bg:          #0d0f14;
    --sidebar-bg:  #0f1219;
    --card-bg:     #161a24;
    --border:      #2a2f3e;
    --border-soft: #1e2330;
    --text:        #c9d1e0;
    --text-head:   #e8d5a3;
    --info-bg:     #161a24;
    --info-text:   #c9d1e0;
    --success-bg:  #0f1f18;
    --success-bdr: #1a3a27;
    --success-txt: #a7f3d0;
    --danger-bg:   #1f0f0f;
    --danger-bdr:  #3a1a1a;
    --danger-txt:  #fca5a5;
    --btn-bg:      #e8d5a3;
    --btn-text:    #0d0f14;
}

/* Light mode tokens */
[data-theme="light"], .stApp[data-theme="light"] {
    --bg:          #f7f5f0;
    --sidebar-bg:  #efece5;
    --card-bg:     #ffffff;
    --border:      #d8d0c0;
    --border-soft: #e0d8cc;
    --text:        #2d2a24;
    --text-head:   #5c3d11;
    --info-bg:     #fdf8ef;
    --info-text:   #4a3820;
    --success-bg:  #f0faf4;
    --success-bdr: #bbf7d0;
    --success-txt: #166534;
    --danger-bg:   #fff5f5;
    --danger-bdr:  #fecaca;
    --danger-txt:  #991b1b;
    --btn-bg:      #b8955a;
    --btn-text:    #ffffff;
}

/* Fallback — match system (default dark for our app) */
@media (prefers-color-scheme: dark) {
    :root {
        --bg: #0d0f14; --sidebar-bg: #0f1219; --card-bg: #161a24;
        --border: #2a2f3e; --border-soft: #1e2330; --text: #c9d1e0;
        --text-head: #e8d5a3; --info-bg: #161a24; --info-text: #c9d1e0;
        --success-bg: #0f1f18; --success-bdr: #1a3a27; --success-txt: #a7f3d0;
        --danger-bg: #1f0f0f; --danger-bdr: #3a1a1a; --danger-txt: #fca5a5;
        --btn-bg: #e8d5a3; --btn-text: #0d0f14;
    }
}
@media (prefers-color-scheme: light) {
    :root {
        --bg: #f7f5f0; --sidebar-bg: #efece5; --card-bg: #ffffff;
        --border: #d8d0c0; --border-soft: #e0d8cc; --text: #2d2a24;
        --text-head: #5c3d11; --info-bg: #fdf8ef; --info-text: #4a3820;
        --success-bg: #f0faf4; --success-bdr: #bbf7d0; --success-txt: #166534;
        --danger-bg: #fff5f5; --danger-bdr: #fecaca; --danger-txt: #991b1b;
        --btn-bg: #b8955a; --btn-text: #ffffff;
    }
}

/* ── Base ── */
[data-testid="stAppViewContainer"] { background: var(--bg) !important; }
[data-testid="stSidebar"]          { background: var(--sidebar-bg) !important; border-right: 1px solid var(--border-soft) !important; }
[data-testid="stHeader"]           { background: transparent !important; }

html, body, .stApp {
    font-family: 'DM Sans', sans-serif;
    color: var(--text);
}

/* ── Typography ── */
h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
    color: var(--text-head);
    letter-spacing: -0.5px;
}
h1 { font-size: 2.2rem; margin-bottom: 4px; }
h2 { font-size: 1.5rem; margin-bottom: 2px; }
h3 { font-size: 1.1rem; }

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px;
    padding: 20px 24px;
}
[data-testid="stMetricLabel"] { color: var(--muted) !important; font-size: 0.8rem !important; letter-spacing: 0.06em; text-transform: uppercase; }
[data-testid="stMetricValue"] { color: var(--text-head) !important; font-family: 'DM Serif Display', serif !important; font-size: 2rem !important; }
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--btn-bg) !important;
    color: var(--btn-text) !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    border: none !important;
    border-radius: 8px;
    padding: 10px 22px;
    transition: opacity 0.15s;
}
.stButton > button:hover { opacity: 0.85; }

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: var(--card-bg) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    border-bottom: 1px solid var(--border);
    gap: 8px;
}
[data-testid="stTabs"] [role="tab"] {
    font-family: 'DM Sans', sans-serif;
    color: var(--muted);
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--accent);
    border-bottom: 2px solid var(--accent);
    background: transparent;
}

/* ── Sidebar user block ── */
.sidebar-user {
    padding: 20px 16px 12px;
    border-bottom: 1px solid var(--border-soft);
    margin-bottom: 8px;
}
.sidebar-user img {
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 2px solid var(--accent-soft);
}
.sidebar-user .user-name {
    font-family: 'DM Serif Display', serif;
    color: var(--text-head);
    font-size: 1rem;
    margin-top: 6px;
}
.sidebar-user .user-email { color: var(--muted); font-size: 0.75rem; }
.admin-badge {
    display: inline-block;
    background: var(--accent);
    color: #fff;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 20px;
    margin-top: 4px;
}

/* ── Section labels ── */
.section-label {
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--muted);
    margin: 24px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid var(--border-soft);
}

/* ── Alert boxes ── */
.info-box {
    background: var(--info-bg);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: var(--info-text);
    margin: 12px 0;
}
.success-box {
    background: var(--success-bg);
    border: 1px solid var(--success-bdr);
    border-left: 3px solid #34d399;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: var(--success-txt);
    margin: 12px 0;
}
.danger-box {
    background: var(--danger-bg);
    border: 1px solid var(--danger-bdr);
    border-left: 3px solid #f87171;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: var(--danger-txt);
    margin: 12px 0;
}

/* ── Score pill ── */
.score-pill {
    display: inline-block;
    background: var(--accent);
    color: #fff;
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
    pic      = user.get("picture", "")
    name     = user.get("name", "User")
    email    = user.get("email", "")
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