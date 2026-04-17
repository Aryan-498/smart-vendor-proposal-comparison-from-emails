"""
User Dashboard — visible to all logged-in users.
Shows: best offers per product, offer history, vendor leaderboard.
"""

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from database.db_manager import get_connection
from processing.offer_comparator import get_best_offers
from inventory.inventory_manager import load_inventory


def _fetch_all_offers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT product, quantity, unit, price, vendor, intent, email_date FROM offers ORDER BY id DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def _fetch_vendors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, total_orders, last_seen FROM vendors ORDER BY total_orders DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def render():
    st.markdown("## Best Offers")
    st.markdown('<div class="section-label">AI-ranked top offers per product</div>', unsafe_allow_html=True)

    best = get_best_offers()

    if not best:
        st.markdown('<div class="info-box">No offers in the database yet. Run the email processor to populate offers.</div>', unsafe_allow_html=True)
    else:
        # Metric row
        cols = st.columns(len(best))
        for i, offer in enumerate(best):
            with cols[i]:
                st.metric(
                    label=offer["product"].upper(),
                    value=f"₹{offer['price']}/kg",
                    delta=f"Score {offer['score']}"
                )

        st.markdown('<div class="section-label">Detailed breakdown</div>', unsafe_allow_html=True)
        df = pd.DataFrame(best)
        df.columns = [c.title() for c in df.columns]
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Offer History ─────────────────────────────────────────────────────────
    st.markdown("## Offer History")
    st.markdown('<div class="section-label">All extracted offers from emails</div>', unsafe_allow_html=True)

    rows = _fetch_all_offers()

    if not rows:
        st.markdown('<div class="info-box">No offer history found.</div>', unsafe_allow_html=True)
    else:
        df_hist = pd.DataFrame(rows, columns=["Product", "Quantity", "Unit", "Price", "Vendor", "Intent", "Date"])
        
        # Filter controls
        col1, col2 = st.columns(2)
        with col1:
            products = ["All"] + sorted(df_hist["Product"].dropna().unique().tolist())
            sel_product = st.selectbox("Filter by product", products)
        with col2:
            intents = ["All"] + sorted(df_hist["Intent"].dropna().unique().tolist())
            sel_intent = st.selectbox("Filter by intent", intents)

        filtered = df_hist.copy()
        if sel_product != "All":
            filtered = filtered[filtered["Product"] == sel_product]
        if sel_intent != "All":
            filtered = filtered[filtered["Intent"] == sel_intent]

        st.dataframe(filtered, use_container_width=True, hide_index=True)

        # Price chart
        if len(filtered) > 1 and sel_product != "All":
            st.markdown('<div class="section-label">Price trend for selected product</div>', unsafe_allow_html=True)
            fig, ax = plt.subplots(figsize=(8, 3))
            fig.patch.set_facecolor("#0d0f14")
            ax.set_facecolor("#161a24")
            ax.plot(
                range(len(filtered)),
                filtered["Price"].values,
                color="#e8d5a3",
                linewidth=2,
                marker="o",
                markersize=4
            )
            ax.set_xlabel("Offer #", color="#6b7280", fontsize=9)
            ax.set_ylabel("Price (₹/kg)", color="#6b7280", fontsize=9)
            ax.tick_params(colors="#6b7280")
            for spine in ax.spines.values():
                spine.set_edgecolor("#2a2f3e")
            st.pyplot(fig)
            plt.close()

    # ── Vendor Leaderboard ────────────────────────────────────────────────────
    st.markdown("## Vendor Leaderboard")
    st.markdown('<div class="section-label">Ranked by total interactions</div>', unsafe_allow_html=True)

    vendors = _fetch_vendors()

    if not vendors:
        st.markdown('<div class="info-box">No vendor data yet.</div>', unsafe_allow_html=True)
    else:
        df_v = pd.DataFrame(vendors, columns=["Vendor", "Total Orders", "Last Seen"])
        df_v.index = range(1, len(df_v) + 1)
        st.dataframe(df_v, use_container_width=True)

    # ── Inventory Snapshot ────────────────────────────────────────────────────
    st.markdown("## Inventory Snapshot")
    st.markdown('<div class="section-label">Current stock levels (read-only)</div>', unsafe_allow_html=True)

    inv = load_inventory()
    if not inv:
        st.markdown('<div class="info-box">Inventory file not found.</div>', unsafe_allow_html=True)
    else:
        inv_rows = [
            {"Product": p.title(), "Stock (kg)": v.get("stock", 0), "Cost Price (₹/kg)": v.get("cost_price", 0)}
            for p, v in inv.items()
        ]
        df_inv = pd.DataFrame(inv_rows)
        st.dataframe(df_inv, use_container_width=True, hide_index=True)