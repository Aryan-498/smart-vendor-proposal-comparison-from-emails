"""
User Dashboard — all logged-in users.
- Inventory: product name, stock, status only (NO cost price)
- Make an Offer: includes phone + address fields
- My Offers: only this user's offers
- Best Offers tab: REMOVED for regular users
"""

import pandas as pd
import streamlit as st

from database.db_manager import get_connection, add_contact_columns
from inventory.inventory_manager import load_inventory, get_available_stock
from processing.normalization import normalize_product


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_web_offer(product, quantity, price, user_email, user_name,
                    phone="", address="", note=""):
    conn = get_connection()
    cursor = conn.cursor()

    # ensure contact columns exist
    add_contact_columns()

    cursor.execute("""
        INSERT INTO offers (product, quantity, unit, price, vendor, intent,
                            email_date, source, user_email, vendor_email,
                            status, phone, address, note)
        VALUES (?, ?, 'kg', ?, ?, 'offer', datetime('now'),
                'web', ?, ?, 'pending', ?, ?, ?)
    """, (product, quantity, price, user_name,
          user_email, user_email, phone, address, note))

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
    add_contact_columns()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product, quantity, unit, price, intent, status, phone, address, email_date
        FROM offers WHERE user_email=? ORDER BY id DESC
    """, (user_email,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ── main render ───────────────────────────────────────────────────────────────

def render(user: dict):
    name  = user["name"]
    email = user["email"]

    tab1, tab2, tab3 = st.tabs([
        "📦 Inventory", "✍ Make an Offer", "📋 My Offers"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory (NO cost price shown)
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("## Current Inventory")
        st.markdown(
            '<div class="info-box">Live inventory — you can submit offers for '
            'quantities within available stock.</div>',
            unsafe_allow_html=True
        )

        inv = load_inventory()
        if not inv:
            st.markdown('<div class="info-box">No inventory data found.</div>',
                        unsafe_allow_html=True)
        else:
            rows = []
            for p, v in inv.items():
                stock = v.get("stock", 0)
                rows.append({
                    "Product":        p.title(),
                    "Available (kg)": stock,
                    # ← cost price intentionally excluded
                    "Status": "✅ In Stock" if stock > 0 else "❌ Out of Stock"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Submit Offer (with phone + address)
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## Submit a New Offer")
        st.markdown(
            f'<div class="info-box">Your offer will be submitted as '
            f'<b>{name}</b> ({email}) and reviewed by our procurement team.</div>',
            unsafe_allow_html=True
        )

        inv = load_inventory()
        products = [p.title() for p in inv.keys()] if inv else []

        if not products:
            st.warning("No products available in inventory right now.")
        else:
            # ── Product + Quantity ─────────────────────────────────────────
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

            price = st.number_input(
                "Your offered price (₹/kg)",
                min_value=1.0, step=0.5, key="offer_price"
            )

            st.markdown('<div class="section-label">Contact Details</div>',
                        unsafe_allow_html=True)

            # ── Contact fields ─────────────────────────────────────────────
            col3, col4 = st.columns(2)
            with col3:
                phone = st.text_input(
                    "Phone number",
                    placeholder="+91 98765 43210",
                    key="offer_phone"
                )
            with col4:
                address = st.text_input(
                    "Business address",
                    placeholder="City, State",
                    key="offer_address"
                )

            note = st.text_area(
                "Additional note (optional)",
                placeholder="e.g. available from next week, bulk discount possible",
                key="offer_note"
            )

            st.markdown("---")
            submit = st.button("📤 Submit Offer", key="submit_offer")

            if submit:
                if not phone.strip():
                    st.markdown(
                        '<div class="danger-box">Please enter a phone number so we can contact you.</div>',
                        unsafe_allow_html=True
                    )
                elif avail == 0:
                    st.markdown(
                        '<div class="danger-box">This product is currently out of stock.</div>',
                        unsafe_allow_html=True
                    )
                elif quantity > avail:
                    st.markdown(
                        f'<div class="danger-box">Quantity {quantity} kg exceeds '
                        f'available stock of {avail} kg.</div>',
                        unsafe_allow_html=True
                    )
                else:
                    norm_product = normalize_product(product_key)
                    _save_web_offer(
                        norm_product, quantity, price,
                        email, name, phone, address, note
                    )
                    st.markdown(
                        f'<div class="success-box">✓ Offer submitted! '
                        f'<b>{quantity} kg</b> of <b>{sel_product}</b> at '
                        f'<b>₹{price}/kg</b>.<br>'
                        f'We will contact you at <b>{phone}</b>. '
                        f'The admin will review it shortly.</div>',
                        unsafe_allow_html=True
                    )
                    st.balloons()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — My Offers (only this user's, shows phone + address)
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## My Offer History")
        st.markdown(
            '<div class="info-box">Only your offers are shown here.</div>',
            unsafe_allow_html=True
        )

        my_rows = _my_offers(email)

        if not my_rows:
            st.markdown(
                '<div class="info-box">No offers yet. Go to '
                '<b>Make an Offer</b> to get started.</div>',
                unsafe_allow_html=True
            )
        else:
            df = pd.DataFrame(my_rows, columns=[
                "Product", "Quantity", "Unit", "Price",
                "Intent", "Status", "Phone", "Address", "Date"
            ])

            def status_badge(s):
                return {
                    "pending": "🟡 Pending",
                    "accepted": "🟢 Accepted",
                    "rejected": "🔴 Rejected",
                    "counter": "🔵 Counter Offer",
                }.get(s, s)

            df["Status"] = df["Status"].apply(status_badge)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown('<div class="section-label">Summary</div>',
                        unsafe_allow_html=True)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Offers", len(df))
            c2.metric("Avg Price (₹/kg)", f"{df['Price'].mean():.1f}")
            c3.metric("Total Quantity (kg)", f"{df['Quantity'].sum():.0f}")