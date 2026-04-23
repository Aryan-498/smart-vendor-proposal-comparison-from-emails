"""
Analytics Dashboard — Admin only.
Charts:
  1. Offers this week vs last week (metric cards)
  2. Offers by product (bar chart)
  3. Average price per product over time (line chart)
  4. Offer status breakdown (pie chart)
  5. Top vendors by volume (bar chart)
"""

import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import streamlit as st
from database.db_manager import get_connection

# ── shared chart style ────────────────────────────────────────────────────────
BG      = "#0d0f14"
CARD_BG = "#161a24"
BORDER  = "#2a2f3e"
GOLD    = "#e8d5a3"
MUTED   = "#6b7280"
COLORS  = ["#e8d5a3", "#7c9cbf", "#7fbf7c", "#bf7c7c", "#bf9d7c", "#a07cbf"]

def _style_fig(fig, ax):
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(CARD_BG)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
    return fig, ax


@st.cache_data(ttl=30, show_spinner=False)
def _fetch_all_offers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product, quantity, price, vendor, status, source, email_date
        FROM offers
        WHERE price > 0 AND product != ''
        ORDER BY email_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    df = pd.DataFrame(rows, columns=["Product","Quantity","Price","Vendor","Status","Source","Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    return df


def render():
    st.markdown("## Analytics")
    st.markdown('<div class="section-label">Live insights from all offer data</div>',
                unsafe_allow_html=True)

    df = _fetch_all_offers()

    if df.empty:
        st.markdown('<div class="info-box">No offer data yet. Run the pipeline or submit some offers to see analytics.</div>',
                    unsafe_allow_html=True)
        return

    # ── Row 1: KPI metrics ────────────────────────────────────────────────────
    now       = pd.Timestamp.now()
    this_week = df[df["Date"] >= now - pd.Timedelta(days=7)]
    last_week = df[(df["Date"] >= now - pd.Timedelta(days=14)) &
                   (df["Date"] <  now - pd.Timedelta(days=7))]
    pending   = df[df["Status"] == "pending"]
    accepted  = df[df["Status"] == "accepted"]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Offers",      len(df))
    c2.metric("This Week",         len(this_week),
              delta=f"{len(this_week)-len(last_week):+d} vs last week")
    c3.metric("Pending Review",    len(pending))
    c4.metric("Accepted",          len(accepted))
    c5.metric("Avg Price (₹/kg)",  f"₹{df['Price'].mean():.1f}")

    st.markdown("---")

    # ── Row 2: Offers by product | Status breakdown ───────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Offers by Product")
        prod_counts = df["Product"].str.title().value_counts()

        fig, ax = plt.subplots(figsize=(5, 3))
        _style_fig(fig, ax)
        bars = ax.barh(prod_counts.index, prod_counts.values,
                       color=COLORS[:len(prod_counts)], height=0.5)
        ax.set_xlabel("Number of Offers", color=MUTED, fontsize=9)
        for bar, val in zip(bars, prod_counts.values):
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                    str(val), va="center", color=GOLD, fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        st.markdown("#### Offer Status Breakdown")
        status_counts = df["Status"].value_counts()
        status_colors = {
            "pending":  "#e8d5a3",
            "accepted": "#7fbf7c",
            "rejected": "#bf7c7c",
            "counter":  "#7c9cbf",
        }
        colors = [status_colors.get(s, "#aaa") for s in status_counts.index]
        labels = [s.title() for s in status_counts.index]

        fig, ax = plt.subplots(figsize=(5, 3))
        fig.patch.set_facecolor(BG)
        wedges, texts, autotexts = ax.pie(
            status_counts.values, labels=labels, colors=colors,
            autopct="%1.0f%%", startangle=140,
            textprops={"color": MUTED, "fontsize": 9}
        )
        for at in autotexts:
            at.set_color(BG)
            at.set_fontweight("bold")
        ax.set_facecolor(BG)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    st.markdown("---")

    # ── Row 3: Avg price trend per product ────────────────────────────────────
    st.markdown("#### Average Price Trend per Product (over time)")

    df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    products   = df["Product"].str.title().unique()

    fig, ax = plt.subplots(figsize=(10, 3.5))
    _style_fig(fig, ax)

    for i, product in enumerate(products):
        subset = df[df["Product"].str.title() == product]
        weekly = subset.groupby("Week")["Price"].mean()
        if len(weekly) >= 1:
            ax.plot(weekly.index, weekly.values,
                    marker="o", linewidth=2, markersize=4,
                    color=COLORS[i % len(COLORS)], label=product)

    ax.set_ylabel("Avg Price (₹/kg)", color=MUTED, fontsize=9)
    ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
              labelcolor=MUTED, fontsize=8)
    ax.grid(axis="y", color=BORDER, linewidth=0.5, linestyle="--")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.markdown("---")

    # ── Row 4: Top vendors + Source split ─────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### Top Vendors by Offer Volume")
        top_vendors = df["Vendor"].value_counts().head(8)

        fig, ax = plt.subplots(figsize=(5, 3.5))
        _style_fig(fig, ax)
        ax.barh(top_vendors.index, top_vendors.values,
                color=GOLD, height=0.5)
        ax.set_xlabel("Offers", color=MUTED, fontsize=9)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col4:
        st.markdown("#### Offer Source (Email vs Web)")
        source_counts = df["Source"].value_counts()
        src_colors    = {"email": GOLD, "web": "#7c9cbf"}
        colors = [src_colors.get(s, "#aaa") for s in source_counts.index]

        fig, ax = plt.subplots(figsize=(5, 3.5))
        fig.patch.set_facecolor(BG)
        ax.pie(source_counts.values,
               labels=[s.title() for s in source_counts.index],
               colors=colors, autopct="%1.0f%%", startangle=90,
               textprops={"color": MUTED, "fontsize": 9})
        ax.set_facecolor(BG)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    st.markdown("---")

    # ── Row 5: Raw weekly offer count bar chart ───────────────────────────────
    st.markdown("#### Weekly Offer Volume")
    weekly_vol = df.groupby("Week").size().reset_index(name="Count")

    fig, ax = plt.subplots(figsize=(10, 2.5))
    _style_fig(fig, ax)
    ax.bar(weekly_vol["Week"].astype(str), weekly_vol["Count"],
           color=GOLD, width=0.5)
    ax.set_ylabel("Offers", color=MUTED, fontsize=9)
    plt.xticks(rotation=30, ha="right", fontsize=8, color=MUTED)
    ax.grid(axis="y", color=BORDER, linewidth=0.5, linestyle="--")
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()
    