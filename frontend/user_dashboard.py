"""
User Dashboard — all logged-in users.

- View inventory (read-only)
- Submit a new offer for any product
- View ONLY their own past offers
- View best offers (AI-ranked, all users)
- View vendor leaderboard
"""

import pandas as pd
import streamlit as st
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from database.db_manager import get_connection
from processing.offer_comparator import get_best_offers
from inventory.inventory_manager import load_inventory, get_available_stock
from processing.normalization import normalize_product


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_web_offer(product, quantity, price, user_email, user_name):
    """Save an offer submitted via the website."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO offers (product, quantity, unit, price, vendor, intent,
                            email_date, source, user_email, vendor_email, status)
        VALUES (?, ?, 'kg', ?, ?, 'offer', datetime('now'), 'web', ?, ?, 'pending')
    """, (product, quantity, price, user_name, user_email, user_email))

    # upsert vendor
    cursor.execute("SELECT id FROM vendors WHERE name=?", (user_name,))
    if cursor.fetchone():
        cursor.execute(
            "UPDATE vendors SET total_orders=total_orders+1, last_seen=datetime('now') WHERE name=?",
            (user_name,)
        )
    else:
        cursor.execute(
            "INSERT INTO vendors (name, total_orders, last_seen) VALUES (?,1,datetime('now'))",
            (user_name,)
        )

    conn.commit()
    conn.close()


def _my_offers(user_email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product, quantity, unit, price, intent, status, email_date
        FROM offers WHERE user_email=? ORDER BY id DESC
    """, (user_email,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def _fetch_vendors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name, total_orders, last_seen FROM vendors ORDER BY total_orders DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return rows


# ── main render ───────────────────────────────────────────────────────────────

def render(user: dict):
    name  = user["name"]
    email = user["email"]

    tab1, tab2, tab3, tab4 = st.tabs([
        "📦 Inventory", "✍ Make an Offer", "📋 My Offers", "🏆 Best Offers"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory (read-only)
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("## Current Inventory")
        st.markdown('<div class="info-box">This is the live inventory. You can only submit offers for quantities within available stock.</div>', unsafe_allow_html=True)

        inv = load_inventory()
        if not inv:
            st.markdown('<div class="info-box">No inventory data found.</div>', unsafe_allow_html=True)
        else:
            rows = []
            for p, v in inv.items():
                stock = v.get("stock", 0)
                rows.append({
                    "Product":         p.title(),
                    "Available (kg)":  stock,
                    "Cost Price (₹/kg)": v.get("cost_price", 0),
                    "Status":          "✅ In Stock" if stock > 0 else "❌ Out of Stock"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Submit Offer
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## Submit a New Offer")
        st.markdown(f'<div class="info-box">Your offer will be submitted as <b>{name}</b> ({email}) and reviewed by our team.</div>', unsafe_allow_html=True)

        inv = load_inventory()
        products = [p.title() for p in inv.keys()] if inv else []

        if not products:
            st.warning("No products available in inventory right now.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                sel_product = st.selectbox("Product", products, key="offer_product")
                product_key = sel_product.lower()
                avail = get_available_stock(product_key)
                st.caption(f"Available stock: **{avail} kg**")

            with col2:
                quantity = st.number_input(
                    "Quantity (kg)",
                    min_value=1.0,
                    max_value=float(avail) if avail > 0 else 1.0,
                    step=10.0,
                    key="offer_qty"
                )

            price = st.number_input("Your offered price (₹/kg)", min_value=1.0, step=0.5, key="offer_price")
            note  = st.text_area("Additional note (optional)", placeholder="e.g. available from next week, bulk discount possible", key="offer_note")

            st.markdown("---")
            col_a, col_b = st.columns([1, 3])
            with col_a:
                submit = st.button("📤 Submit Offer", key="submit_offer")

            if submit:
                if avail == 0:
                    st.markdown('<div class="danger-box">This product is currently out of stock. Offers cannot be submitted.</div>', unsafe_allow_html=True)
                elif quantity > avail:
                    st.markdown(f'<div class="danger-box">Quantity {quantity} kg exceeds available stock of {avail} kg.</div>', unsafe_allow_html=True)
                else:
                    norm_product = normalize_product(product_key)
                    _save_web_offer(norm_product, quantity, price, email, name)
                    st.markdown(f'<div class="success-box">✓ Offer submitted! <b>{quantity} kg</b> of <b>{sel_product}</b> at <b>₹{price}/kg</b>. The admin will review it shortly.</div>', unsafe_allow_html=True)
                    st.balloons()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — My Offers (only this user's)
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## My Offer History")
        st.markdown('<div class="info-box">Only your offers are shown here. Other users cannot see your offers.</div>', unsafe_allow_html=True)

        my_rows = _my_offers(email)

        if not my_rows:
            st.markdown('<div class="info-box">You have not submitted any offers yet. Go to the <b>Make an Offer</b> tab to get started.</div>', unsafe_allow_html=True)
        else:
            df = pd.DataFrame(my_rows, columns=["Product","Quantity","Unit","Price","Intent","Status","Date"])

            # Color status
            def status_badge(s):
                colors = {
                    "pending":       "🟡 Pending",
                    "accepted":      "🟢 Accepted",
                    "rejected":      "🔴 Rejected",
                    "counter":       "🔵 Counter Offer",
                }
                return colors.get(s, s)

            df["Status"] = df["Status"].apply(status_badge)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Stats
            st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Offers", len(df))
            c2.metric("Avg Price (₹/kg)", f"{df['Price'].mean():.1f}")
            c3.metric("Total Quantity (kg)", f"{df['Quantity'].sum():.0f}")

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Best Offers (AI-ranked, visible to all)
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("## Best Offers (AI Ranked)")
        st.markdown('<div class="info-box">The AI ranks all offers by profit, quantity, vendor reliability, and intent to find the best deal per product.</div>', unsafe_allow_html=True)

        best = get_best_offers()

        if not best:
            st.markdown('<div class="info-box">No ranked offers yet. Offers will appear here once processed.</div>', unsafe_allow_html=True)
        else:
            cols = st.columns(min(len(best), 4))
            for i, offer in enumerate(best[:4]):
                with cols[i]:
                    st.metric(offer["product"].upper(), f"₹{offer['price']}/kg", f"Score {offer['score']}")

            df_best = pd.DataFrame(best)
            df_best.columns = [c.title() for c in df_best.columns]
            st.dataframe(df_best, use_container_width=True, hide_index=True)

        # Vendor leaderboard
        st.markdown("## Vendor Leaderboard")
        vendors = _fetch_vendors()
        if vendors:
            df_v = pd.DataFrame(vendors, columns=["Vendor","Total Orders","Last Seen"])
            df_v.index = range(1, len(df_v)+1)
            st.dataframe(df_v, use_container_width=True)