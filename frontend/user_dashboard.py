"""
User Dashboard — all logged-in users.
- Inventory: product + stock (NO cost price)
- Make an Offer
- My Offers: with Accept/Decline buttons for counter offers
"""

import pandas as pd
import streamlit as st

from database.db_manager import get_connection, add_contact_columns
from inventory.inventory_manager import load_inventory, get_available_stock
from processing.normalization import normalize_product
from config.settings import ADMIN_EMAIL


# ── helpers ───────────────────────────────────────────────────────────────────

def _save_web_offer(product, quantity, price, user_email, user_name,
                    phone="", address="", note=""):
    add_contact_columns()
    conn = get_connection()
    cursor = conn.cursor()
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
        SELECT id, product, quantity, unit, price, counter_price,
               status, user_response, phone, address, email_date
        FROM offers WHERE user_email=? ORDER BY id DESC
    """, (user_email,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def _set_user_response(offer_id, response):
    """Save user's response (accepted/declined) to counter offer."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE offers SET user_response=?, status=? WHERE id=?",
        (response, "accepted" if response == "accepted" else "counter_declined", offer_id)
    )
    conn.commit()
    conn.close()


def _pending_counter_count(user_email):
    """Count how many counter offers are awaiting user response."""
    add_contact_columns()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM offers
        WHERE user_email=? AND status='counter' AND user_response IS NULL
    """, (user_email,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


# ── main render ───────────────────────────────────────────────────────────────

def render(user: dict):
    name  = user["name"]
    email = user["email"]

    # Show alert banner if there are pending counter offers
    pending = _pending_counter_count(email)
    if pending > 0:
        st.markdown(
            f'<div class="danger-box">🔵 You have <b>{pending} counter offer{"s" if pending > 1 else ""}</b> '
            f'waiting for your response! Go to <b>My Offers</b> tab to respond.</div>',
            unsafe_allow_html=True
        )

    tab1, tab2, tab3 = st.tabs([
        "📦 Inventory",
        "✍ Make an Offer",
        f"📋 My Offers {'🔵' * pending if pending else ''}"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("## Current Inventory")
        st.markdown(
            '<div class="info-box">Live inventory — submit offers for quantities within available stock.</div>',
            unsafe_allow_html=True
        )
        inv = load_inventory()
        if not inv:
            st.markdown('<div class="info-box">No inventory data found.</div>', unsafe_allow_html=True)
        else:
            rows = [
                {"Product": p.title(), "Available (kg)": v.get("stock", 0),
                 "Status": "✅ In Stock" if v.get("stock", 0) > 0 else "❌ Out of Stock"}
                for p, v in inv.items()
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Submit Offer
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## Submit a New Offer")
        st.markdown(
            f'<div class="info-box">Submitting as <b>{name}</b> ({email}). '
            f'Our team will review and respond.</div>',
            unsafe_allow_html=True
        )

        inv      = load_inventory()
        products = [p.title() for p in inv.keys()] if inv else []

        if not products:
            st.warning("No products available right now.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                sel_product = st.selectbox("Product", products, key="offer_product")
                product_key = sel_product.lower()
                avail       = get_available_stock(product_key)
                st.caption(f"Available stock: **{avail} kg**")
            with col2:
                quantity = st.number_input(
                    "Quantity (kg)", min_value=1.0,
                    max_value=float(avail) if avail > 0 else 1.0,
                    step=10.0, key="offer_qty"
                )

            price = st.number_input("Your price (₹/kg)", min_value=1.0, step=0.5, key="offer_price")

            st.markdown('<div class="section-label">Contact Details</div>', unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                phone = st.text_input("Phone number *", placeholder="+91 98765 43210", key="offer_phone")
            with col4:
                address = st.text_input("Business address", placeholder="City, State", key="offer_address")

            note = st.text_area("Additional note (optional)", key="offer_note")
            st.markdown("---")

            if st.button("📤 Submit Offer", key="submit_offer"):
                if not phone.strip():
                    st.markdown('<div class="danger-box">Phone number is required.</div>', unsafe_allow_html=True)
                elif avail == 0:
                    st.markdown('<div class="danger-box">Product is out of stock.</div>', unsafe_allow_html=True)
                elif quantity > avail:
                    st.markdown(f'<div class="danger-box">Exceeds available stock of {avail} kg.</div>', unsafe_allow_html=True)
                else:
                    _save_web_offer(normalize_product(product_key), quantity,
                                    price, email, name, phone, address, note)
                    st.markdown(
                        f'<div class="success-box">✓ Offer submitted — '
                        f'<b>{quantity} kg</b> of <b>{sel_product}</b> at <b>₹{price}/kg</b>.<br>'
                        f'We will contact you at <b>{phone}</b>.</div>',
                        unsafe_allow_html=True
                    )
                    st.balloons()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — My Offers + Counter Offer Response
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## My Offer History")

        my_rows = _my_offers(email)

        if not my_rows:
            st.markdown(
                '<div class="info-box">No offers yet. Go to <b>Make an Offer</b> to get started.</div>',
                unsafe_allow_html=True
            )
            return

        # ── Counter offers awaiting response (shown prominently at top) ───────
        counter_pending = [
            r for r in my_rows
            if r[6] == "counter" and r[7] is None  # status=counter, user_response=None
        ]

        if counter_pending:
            st.markdown("### 🔵 Counter Offers — Action Required")
            st.markdown(
                '<div class="info-box">The admin has sent you a counter offer. '
                'Please accept or decline below.</div>',
                unsafe_allow_html=True
            )

            for row in counter_pending:
                offer_id, product, quantity, unit, orig_price, counter_price, \
                    status, user_response, phone, address, date = row

                orig_total    = orig_price * quantity
                counter_total = counter_price * quantity if counter_price else 0

                st.markdown(f"""
                <div style="background:var(--card-bg,#161a24);border:1px solid #7c9cbf;
                     border-left:4px solid #7c9cbf;border-radius:10px;
                     padding:18px 22px;margin:12px 0;">
                    <div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;
                         letter-spacing:0.08em;margin-bottom:8px;">Counter Offer #{offer_id}</div>
                    <div style="font-size:1.1rem;font-weight:500;margin-bottom:4px;">
                        {product.title()} — {quantity} kg
                    </div>
                    <div style="margin:8px 0;">
                        <span style="color:#6b7280;font-size:0.85rem;">Your original price:</span>
                        <span style="text-decoration:line-through;color:#6b7280;margin-left:6px;">
                            ₹{orig_price}/kg
                        </span>
                    </div>
                    <div style="margin:4px 0 16px;">
                        <span style="color:#6b7280;font-size:0.85rem;">Admin counter price:</span>
                        <span style="font-size:1.4rem;font-weight:600;color:#7c9cbf;margin-left:8px;">
                            ₹{counter_price}/kg
                        </span>
                        {"&nbsp;<span style='font-size:0.8rem;color:#34d399;'>▼ lower</span>" if counter_price < orig_price else
                         "&nbsp;<span style='font-size:0.8rem;color:#f87171;'>▲ higher</span>" if counter_price > orig_price else ""}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b, _ = st.columns([1, 1, 3])

                with col_a:
                    if st.button("✅ Accept", key=f"accept_{offer_id}", use_container_width=True):
                        from inventory.inventory_manager import deduct_stock

                        # Deduct stock first — check availability
                        deducted = deduct_stock(product, quantity)

                        if not deducted:
                            st.markdown(
                                f'<div class="danger-box">⚠ Sorry — insufficient stock to '
                                f'fulfil <b>{quantity} kg</b> of <b>{product.title()}</b> '
                                f'right now. Please contact us directly.</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            _set_user_response(offer_id, "accepted")

                            # Notify admin
                            try:
                                from gmail.email_sender import notify_admin_counter_response
                                notify_admin_counter_response(
                                    ADMIN_EMAIL, name, email,
                                    product, quantity, counter_price, "accepted"
                                )
                            except Exception:
                                pass  # don't block UI if email fails

                            st.markdown(
                                f'<div class="success-box">✓ You accepted the counter offer of '
                                f'<b>₹{counter_price}/kg</b> for <b>{product.title()}</b>. '
                                f'<b>{quantity} kg</b> has been reserved from inventory. '
                                f'The admin has been notified.</div>',
                                unsafe_allow_html=True
                            )
                            st.rerun()

                with col_b:
                    if st.button("❌ Decline", key=f"decline_{offer_id}", use_container_width=True):
                        _set_user_response(offer_id, "declined")

                        # Notify admin
                        try:
                            from gmail.email_sender import notify_admin_counter_response
                            notify_admin_counter_response(
                                ADMIN_EMAIL, name, email,
                                product, quantity, counter_price, "declined"
                            )
                        except Exception as e:
                            pass

                        st.markdown(
                            f'<div class="danger-box">You declined the counter offer for '
                            f'<b>{product.title()}</b>. The admin has been notified.</div>',
                            unsafe_allow_html=True
                        )
                        st.rerun()

            st.markdown("---")

        # ── Full offer history table ───────────────────────────────────────────
        st.markdown("### All My Offers")

        def fmt_status(row):
            s  = row[6]
            ur = row[7]
            mapping = {
                "pending":          "🟡 Pending",
                "accepted":         "🟢 Accepted",
                "rejected":         "🔴 Rejected",
                "counter":          "🔵 Counter Offer — Awaiting your response" if not ur else f"🔵 Counter — You {ur.title()}",
                "counter_declined": "⚫ Counter Declined",
            }
            return mapping.get(s, s)

        display_rows = []
        for row in my_rows:
            offer_id, product, quantity, unit, orig_price, counter_price, \
                status, user_response, phone, address, date = row

            effective_price = counter_price if counter_price else orig_price
            total = effective_price * quantity
            display_rows.append({
                "Product":       product.title(),
                "Qty (kg)":      quantity,
                "Your Price":    f"₹{orig_price}/kg",
                "Counter Price": f"₹{counter_price}/kg" if counter_price else "—",
                "Total (₹)":     f"₹{total:,.0f}",
                "Status":        fmt_status(row),
                "Phone":         phone or "—",
                "Date":          date,
            })

        df = pd.DataFrame(display_rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Offers", len(my_rows))
        prices = [r[4] for r in my_rows if r[4]]
        c2.metric("Avg Price (₹/kg)", f"{sum(prices)/len(prices):.1f}" if prices else "—")
        c3.metric("Total Qty (kg)", f"{sum(r[2] for r in my_rows):.0f}")