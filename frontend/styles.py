def inject_css():
    import streamlit as st

    # Detect current theme
    try:
        is_light = st.get_option("theme.base") == "light"
    except Exception:
        is_light = False

    if is_light:
        bg          = "#f7f5f0"
        sidebar_bg  = "#efece5"
        card_bg     = "#ffffff"
        border      = "#d8d0c0"
        border_soft = "#e0d8cc"
        text        = "#2d2a24"
        text_head   = "#5c3d11"
        muted       = "#8a7560"
        accent      = "#b8955a"
        accent_soft = "#d4aa70"
        info_bg     = "#fdf8ef"
        info_text   = "#4a3820"
        success_bg  = "#f0faf4"
        success_bdr = "#bbf7d0"
        success_txt = "#166534"
        danger_bg   = "#fff5f5"
        danger_bdr  = "#fecaca"
        danger_txt  = "#991b1b"
        btn_bg      = "#b8955a"
        btn_text    = "#ffffff"
        input_bg    = "#ffffff"
    else:
        bg          = "#0d0f14"
        sidebar_bg  = "#0f1219"
        card_bg     = "#161a24"
        border      = "#2a2f3e"
        border_soft = "#1e2330"
        text        = "#c9d1e0"
        text_head   = "#e8d5a3"
        muted       = "#6b7280"
        accent      = "#e8d5a3"
        accent_soft = "#e8d5a3"
        info_bg     = "#161a24"
        info_text   = "#c9d1e0"
        success_bg  = "#0f1f18"
        success_bdr = "#1a3a27"
        success_txt = "#a7f3d0"
        danger_bg   = "#1f0f0f"
        danger_bdr  = "#3a1a1a"
        danger_txt  = "#fca5a5"
        btn_bg      = "#e8d5a3"
        btn_text    = "#0d0f14"
        input_bg    = "#161a24"

    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,300&display=swap');

[data-testid="stAppViewContainer"] {{ background: {bg} !important; }}
[data-testid="stSidebar"]          {{ background: {sidebar_bg} !important; border-right: 1px solid {border_soft} !important; }}
[data-testid="stHeader"]           {{ background: transparent !important; }}

html, body, .stApp {{ font-family: 'DM Sans', sans-serif; color: {text}; }}

h1, h2, h3 {{
    font-family: 'DM Serif Display', serif;
    color: {text_head};
    letter-spacing: -0.5px;
}}
h1 {{ font-size: 2.2rem; margin-bottom: 4px; }}
h2 {{ font-size: 1.5rem; margin-bottom: 2px; }}
h3 {{ font-size: 1.1rem; }}

[data-testid="stMetric"] {{
    background: {card_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 12px;
    padding: 20px 24px;
}}
[data-testid="stMetricLabel"] {{ color: {muted} !important; font-size: 0.8rem !important; letter-spacing: 0.06em; text-transform: uppercase; }}
[data-testid="stMetricValue"] {{ color: {text_head} !important; font-family: 'DM Serif Display', serif !important; font-size: 2rem !important; }}
[data-testid="stMetricDelta"] {{ font-size: 0.8rem !important; }}

[data-testid="stDataFrame"] {{
    border: 1px solid {border};
    border-radius: 10px;
    overflow: hidden;
}}

.stButton > button {{
    background: {btn_bg} !important;
    color: {btn_text} !important;
    font-family: 'DM Sans', sans-serif;
    font-weight: 500;
    border: none !important;
    border-radius: 8px;
    padding: 10px 22px;
    transition: opacity 0.15s;
}}
.stButton > button:hover {{ opacity: 0.85; }}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    color: {text} !important;
    border-radius: 8px !important;
}}

[data-testid="stTabs"] [role="tablist"] {{
    border-bottom: 1px solid {border};
    gap: 8px;
}}
[data-testid="stTabs"] [role="tab"] {{
    font-family: 'DM Sans', sans-serif;
    color: {muted};
    font-size: 0.85rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    padding: 8px 16px;
    border-radius: 6px 6px 0 0;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: {accent};
    border-bottom: 2px solid {accent};
    background: transparent;
}}

.sidebar-user {{
    padding: 20px 16px 12px;
    border-bottom: 1px solid {border_soft};
    margin-bottom: 8px;
}}
.sidebar-user img {{
    width: 38px; height: 38px;
    border-radius: 50%;
    border: 2px solid {accent_soft};
}}
.sidebar-user .user-name {{
    font-family: 'DM Serif Display', serif;
    color: {text_head};
    font-size: 1rem;
    margin-top: 6px;
}}
.sidebar-user .user-email {{ color: {muted}; font-size: 0.75rem; }}

.admin-badge {{
    display: inline-block;
    background: {accent};
    color: {btn_text};
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 20px;
    margin-top: 4px;
}}

.section-label {{
    font-size: 0.72rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: {muted};
    margin: 24px 0 8px;
    padding-bottom: 4px;
    border-bottom: 1px solid {border_soft};
}}

.info-box {{
    background: {info_bg};
    border: 1px solid {border};
    border-left: 3px solid {accent};
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: {info_text};
    margin: 12px 0;
}}
.success-box {{
    background: {success_bg};
    border: 1px solid {success_bdr};
    border-left: 3px solid #34d399;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: {success_txt};
    margin: 12px 0;
}}
.danger-box {{
    background: {danger_bg};
    border: 1px solid {danger_bdr};
    border-left: 3px solid #f87171;
    border-radius: 8px;
    padding: 14px 18px;
    font-size: 0.88rem;
    color: {danger_txt};
    margin: 12px 0;
}}

.score-pill {{
    display: inline-block;
    background: {accent};
    color: {btn_text};
    font-size: 0.75rem;
    font-weight: 600;
    padding: 3px 10px;
    border-radius: 20px;
}}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


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