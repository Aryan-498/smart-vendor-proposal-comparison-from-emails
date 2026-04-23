"""
User Dashboard — all logged-in users.
Features:
  - Inventory (no cost price)
  - Make an Offer (min order enforced, email confirmation)
  - My Offers (search/filter, counter response, user counter-proposal)
"""

import pandas as pd
import streamlit as st
from datetime import datetime

from database.db_manager import get_connection, create_tables, is_blacklisted
from inventory.inventory_manager import (
    load_inventory, get_available_stock, get_min_order
)
from processing.normalization import normalize_product
from config.settings import ADMIN_EMAIL


# ── cached read functions (ttl=30s — auto-invalidated after writes) ────────────

@st.cache_data(ttl=30, show_spinner=False)
def _cached_inventory():
    """Cache inventory reads — refreshes every 30s or on manual refresh."""
    return load_inventory()


@st.cache_data(ttl=30, show_spinner=False)
def _cached_my_offers(user_email: str):
    """Cache per-user offer reads."""
    create_tables()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, product, quantity, unit, price, counter_price,
               user_counter_price, status, user_response, phone, address,
               email_date
        FROM offers WHERE user_email=? ORDER BY id DESC
    """, (user_email,))
    rows = cursor.fetchall()
    conn.close()
    return rows


@st.cache_data(ttl=30, show_spinner=False)
def _cached_pending_counter_count(user_email: str) -> int:
    """Cache pending counter count — refreshes every 30s."""
    create_tables()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM offers
        WHERE user_email=? AND status='counter' AND user_response IS NULL
    """, (user_email,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


@st.cache_data(ttl=30, show_spinner=False)
def _cached_is_blacklisted(email: str) -> bool:
    """Cache blacklist check."""
    return is_blacklisted(email)


def _invalidate_user_cache(user_email: str):
    """Call after any write to clear cached data for this user."""
    _cached_my_offers.clear()
    _cached_pending_counter_count.clear()
    _cached_inventory.clear()


# ── DB helpers ────────────────────────────────────────────────────────────────

def _save_web_offer(product, quantity, price, user_email, user_name,
                    phone="", address="", note=""):
    create_tables()
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
            (user_name,))
    else:
        cursor.execute(
            "INSERT INTO vendors (name, total_orders, last_seen) VALUES (?,1,datetime('now'))",
            (user_name,))
    conn.commit()
    conn.close()
    _invalidate_user_cache(user_email)


def _my_offers(user_email):
    return _cached_my_offers(user_email)


def _set_user_response(offer_id, response):
    conn = get_connection()
    cursor = conn.cursor()
    new_status = "accepted" if response == "accepted" else "counter_declined"
    cursor.execute(
        "UPDATE offers SET user_response=?, status=? WHERE id=?",
        (response, new_status, offer_id))
    conn.commit()
    conn.close()


def _save_user_counter(offer_id, user_counter_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE offers SET user_counter_price=?, status='user_counter' WHERE id=?",
        (user_counter_price, offer_id))
    conn.commit()
    conn.close()


def _pending_counter_count(user_email):
    return _cached_pending_counter_count(user_email)


# ── main render ───────────────────────────────────────────────────────────────

def render(user: dict):
    name  = user["name"]
    email = user["email"]

    # Blacklist check
    if _cached_is_blacklisted(email):
        st.markdown(
            '<div class="danger-box">⛔ Your account has been restricted from '
            'submitting offers. Please contact the admin for more information.</div>',
            unsafe_allow_html=True)
        return

    pending = _pending_counter_count(email)
    if pending > 0:
        st.markdown(
            f'<div class="danger-box">🔵 You have <b>{pending} counter offer'
            f'{"s" if pending > 1 else ""}</b> waiting for your response! '
            f'Check the <b>My Offers</b> tab.</div>',
            unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "📦 Inventory",
        "✍ Make an Offer",
        f"📋 My Offers{'  🔵' * pending if pending else ''}"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory (no cost price)
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("## Current Inventory")
        st.markdown('<div class="info-box">Live inventory. Submit offers only for quantities within available stock and above the minimum order.</div>',
                    unsafe_allow_html=True)
        inv = _cached_inventory()
        if not inv:
            st.markdown('<div class="info-box">No inventory data found.</div>', unsafe_allow_html=True)
        else:
            rows = []
            for p, v in inv.items():
                stock = v.get("stock", 0)
                rows.append({
                    "Product":          p.title(),
                    "Available (kg)":   stock,
                    "Min Order (kg)":   v.get("min_order", 1),
                    "Status":           "✅ In Stock" if stock > 0 else "❌ Out of Stock"
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Make an Offer
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("## Submit a New Offer")
        st.markdown(
            f'<div class="info-box">Submitting as <b>{name}</b> ({email}). '
            f'You will receive an email confirmation immediately.</div>',
            unsafe_allow_html=True)

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
                min_order   = get_min_order(product_key)
                st.caption(f"Available: **{avail} kg** | Min order: **{min_order} kg**")
            with col2:
                quantity = st.number_input(
                    "Quantity (kg)",
                    min_value=float(min_order),
                    max_value=float(avail) if avail > 0 else float(min_order),
                    value=float(min_order),
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

            # Live total preview
            if quantity and price:
                st.markdown(
                    f'<div class="info-box">💰 <b>Total value:</b> ₹{quantity * price:,.0f} '
                    f'({quantity} kg × ₹{price}/kg)</div>',
                    unsafe_allow_html=True)

            st.markdown("---")
            if st.button("📤 Submit Offer", key="submit_offer"):
                if not phone.strip():
                    st.markdown('<div class="danger-box">Phone number is required.</div>', unsafe_allow_html=True)
                elif avail == 0:
                    st.markdown('<div class="danger-box">Product is out of stock.</div>', unsafe_allow_html=True)
                elif quantity < min_order:
                    st.markdown(f'<div class="danger-box">Minimum order is <b>{min_order} kg</b>.</div>', unsafe_allow_html=True)
                elif quantity > avail:
                    st.markdown(f'<div class="danger-box">Exceeds available stock of {avail} kg.</div>', unsafe_allow_html=True)
                else:
                    norm = normalize_product(product_key)
                    _save_web_offer(norm, quantity, price, email, name, phone, address, note)

                    # Send confirmation email
                    try:
                        from gmail.email_sender import send_offer_confirmation
                        send_offer_confirmation(email, name, norm, quantity, price, phone)
                    except Exception:
                        pass

                    st.markdown(
                        f'<div class="success-box">✓ Offer submitted! '
                        f'<b>{quantity} kg</b> of <b>{sel_product}</b> at '
                        f'<b>₹{price}/kg</b> — Total: <b>₹{quantity*price:,.0f}</b><br>'
                        f'📧 Confirmation sent to <b>{email}</b>.</div>',
                        unsafe_allow_html=True)
                    st.balloons()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — My Offers
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("## My Offer History")

        my_rows = _my_offers(email)

        if not my_rows:
            st.markdown('<div class="info-box">No offers yet. Go to <b>Make an Offer</b> to get started.</div>',
                        unsafe_allow_html=True)
            return

        # ── Search & Filter ───────────────────────────────────────────────────
        with st.expander("🔍 Search & Filter", expanded=False):
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                all_products = ["All"] + sorted({r[1].title() for r in my_rows})
                f_product = st.selectbox("Product", all_products, key="f_prod")
            with fc2:
                all_statuses = ["All", "🟡 Pending", "🟢 Accepted", "🔴 Rejected",
                                "🔵 Counter", "⚫ Declined", "🔄 My Counter"]
                f_status = st.selectbox("Status", all_statuses, key="f_stat")
            with fc3:
                f_search = st.text_input("Search vendor/product", key="f_search")

            dc1, dc2 = st.columns(2)
            with dc1:
                f_date_from = st.date_input("From date", value=None, key="f_dfrom")
            with dc2:
                f_date_to = st.date_input("To date", value=None, key="f_dto")

        # ── Counter offers awaiting response ──────────────────────────────────
        counter_pending = [
            r for r in my_rows
            if r[7] == "counter" and r[8] is None
        ]

        if counter_pending:
            st.markdown("### 🔵 Counter Offers — Action Required")
            st.markdown('<div class="info-box">The admin has sent you a counter offer. Accept, Decline, or propose your own price.</div>',
                        unsafe_allow_html=True)

            for row in counter_pending:
                (offer_id, product, quantity, unit, orig_price, counter_price,
                 user_counter_price, status, user_response, phone, address, date) = row

                orig_total    = orig_price * quantity
                counter_total = counter_price * quantity if counter_price else 0

                st.markdown(f"""
                <div style="background:var(--card-bg,#161a24);border:1px solid #7c9cbf;
                     border-left:4px solid #7c9cbf;border-radius:10px;
                     padding:18px 22px;margin:12px 0;">
                    <div style="font-size:0.75rem;color:#6b7280;text-transform:uppercase;
                         letter-spacing:0.08em;margin-bottom:8px;">Counter Offer #{offer_id}</div>
                    <div style="font-size:1.1rem;font-weight:500;margin-bottom:12px;">
                        {product.title()} — {quantity} kg
                    </div>
                    <div style="display:flex;gap:32px;flex-wrap:wrap;margin-bottom:8px;">
                        <div>
                            <div style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">Your Price</div>
                            <div style="text-decoration:line-through;color:#6b7280;">₹{orig_price}/kg</div>
                            <div style="color:#6b7280;font-size:0.8rem;">Total: ₹{orig_total:,.0f}</div>
                        </div>
                        <div style="align-self:center;color:#6b7280;font-size:1.4rem;">→</div>
                        <div>
                            <div style="color:#6b7280;font-size:0.75rem;text-transform:uppercase;">Counter Price</div>
                            <div style="font-size:1.3rem;font-weight:600;color:#7c9cbf;">₹{counter_price}/kg
                                {"&nbsp;▼" if counter_price < orig_price else "&nbsp;▲" if counter_price > orig_price else ""}
                            </div>
                            <div style="color:#7c9cbf;font-size:0.85rem;">Total: ₹{counter_total:,.0f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                col_a, col_b, col_c = st.columns([1, 1, 2])

                with col_a:
                    if st.button("✅ Accept", key=f"accept_{offer_id}", use_container_width=True):
                        from inventory.inventory_manager import deduct_stock
                        deducted = deduct_stock(product, quantity)
                        if not deducted:
                            st.markdown('<div class="danger-box">⚠ Insufficient stock. Contact admin.</div>',
                                        unsafe_allow_html=True)
                        else:
                            _set_user_response(offer_id, "accepted")
                            _invalidate_user_cache(email)
                            try:
                                from gmail.email_sender import notify_admin_counter_response
                                notify_admin_counter_response(
                                    ADMIN_EMAIL, name, email,
                                    product, quantity, counter_price, "accepted")
                            except Exception:
                                pass
                            st.markdown(
                                f'<div class="success-box">✓ Accepted ₹{counter_price}/kg — '
                                f'Total ₹{counter_total:,.0f}. Admin notified.</div>',
                                unsafe_allow_html=True)
                            st.rerun()

                with col_b:
                    if st.button("❌ Decline", key=f"decline_{offer_id}", use_container_width=True):
                        _set_user_response(offer_id, "declined")
                        _invalidate_user_cache(email)
                        try:
                            from gmail.email_sender import notify_admin_counter_response
                            notify_admin_counter_response(
                                ADMIN_EMAIL, name, email,
                                product, quantity, counter_price, "declined")
                        except Exception:
                            pass
                        st.markdown('<div class="danger-box">Declined. Admin notified.</div>',
                                    unsafe_allow_html=True)
                        st.rerun()

                with col_c:
                    # User counter-proposal
                    with st.expander("🔄 Propose your price instead"):
                        user_cp = st.number_input(
                            "Your counter price (₹/kg)",
                            min_value=0.1,
                            value=float(counter_price) if counter_price else float(orig_price),
                            step=0.5,
                            key=f"ucp_{offer_id}"
                        )
                        st.caption(f"Total at this price: ₹{user_cp * quantity:,.0f}")
                        if st.button("📤 Send Counter", key=f"send_ucp_{offer_id}"):
                            _save_user_counter(offer_id, user_cp)
                            _invalidate_user_cache(email)
                            try:
                                from gmail.email_sender import notify_admin_user_counter
                                notify_admin_user_counter(
                                    ADMIN_EMAIL, name, email,
                                    product, quantity, counter_price, user_cp)
                            except Exception:
                                pass
                            st.markdown(
                                f'<div class="success-box">✓ Counter proposal of '
                                f'₹{user_cp}/kg sent to admin.</div>',
                                unsafe_allow_html=True)
                            st.rerun()

            st.markdown("---")

        # ── Build display table ───────────────────────────────────────────────
        def fmt_status(row):
            s, ur = row[7], row[8]
            return {
                "pending":          "🟡 Pending",
                "accepted":         "🟢 Accepted",
                "rejected":         "🔴 Rejected",
                "counter":          "🔵 Counter — Respond above" if not ur else f"🔵 Counter ({ur.title()})",
                "counter_declined": "⚫ Counter Declined",
                "user_counter":     "🔄 My Counter Sent",
            }.get(s, s)

        display_rows = []
        for row in my_rows:
            (offer_id, product, quantity, unit, orig_price, counter_price,
             user_counter_price, status, user_response, phone, address, date) = row

            eff_price = counter_price if counter_price else orig_price
            total     = eff_price * quantity

            display_rows.append({
                "_id":           offer_id,
                "_status_raw":   status,
                "Product":       product.title(),
                "Qty (kg)":      quantity,
                "Your Price":    f"₹{orig_price}/kg",
                "Counter Price": f"₹{counter_price}/kg" if counter_price else "—",
                "My Counter":    f"₹{user_counter_price}/kg" if user_counter_price else "—",
                "Total (₹)":    f"₹{total:,.0f}",
                "Status":        fmt_status(row),
                "Date":          date,
            })

        df = pd.DataFrame(display_rows)

        # Apply filters
        filtered = df.copy()
        if f_product != "All":
            filtered = filtered[filtered["Product"] == f_product]
        if f_status != "All":
            status_map = {
                "🟡 Pending": "pending", "🟢 Accepted": "accepted",
                "🔴 Rejected": "rejected", "🔵 Counter": "counter",
                "⚫ Declined": "counter_declined", "🔄 My Counter": "user_counter"
            }
            raw = status_map.get(f_status)
            if raw:
                filtered = filtered[filtered["_status_raw"] == raw]
        if f_search:
            mask = filtered["Product"].str.contains(f_search, case=False, na=False)
            filtered = filtered[mask]
        if f_date_from:
            filtered = filtered[pd.to_datetime(filtered["Date"], errors="coerce").dt.date >= f_date_from]
        if f_date_to:
            filtered = filtered[pd.to_datetime(filtered["Date"], errors="coerce").dt.date <= f_date_to]

        st.markdown(f"### All My Offers ({len(filtered)} shown)")

        show_cols = ["Product","Qty (kg)","Your Price","Counter Price","My Counter","Total (₹)","Status","Date"]
        st.dataframe(filtered[show_cols], use_container_width=True, hide_index=True)

        # Summary metrics
        st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Offers", len(my_rows))
        c2.metric("Pending", sum(1 for r in my_rows if r[7] == "pending"))
        c3.metric("Accepted", sum(1 for r in my_rows if r[7] == "accepted"))
        prices = [r[4] for r in my_rows if r[4]]
        c4.metric("Avg Price (₹/kg)", f"{sum(prices)/len(prices):.1f}" if prices else "—")