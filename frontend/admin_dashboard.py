"""
Admin Dashboard — ADMIN_EMAIL only.
Tabs: Inventory | Offers & Actions | Vendors | Analytics | Run Pipeline
"""

import pandas as pd
import streamlit as st

from inventory.inventory_manager import (
    load_inventory, update_inventory, save_inventory,
    reload_inventory, deduct_stock
)
from database.db_manager import get_connection
from gmail.email_sender import (
    send_counter_offer, send_rejection,
    send_acceptance, notify_user_status
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _delete_product(product):
    inv = load_inventory()
    if product in inv:
        del inv[product]
        save_inventory(inv)
        reload_inventory()
        return True
    return False


def _get_offers(start_date=None, end_date=None):
    conn = get_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT id, product, quantity, unit, price, vendor, vendor_email,
                   intent, source, status, phone, address, user_email, email_date
            FROM offers
            WHERE date(email_date) BETWEEN date(?) AND date(?)
            ORDER BY id DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, product, quantity, unit, price, vendor, vendor_email,
                   intent, source, status, phone, address, user_email, email_date
            FROM offers ORDER BY id DESC LIMIT 300
        """)
    rows = cursor.fetchall()
    cols = ["ID","Product","Qty","Unit","Price","Vendor","Vendor Email",
            "Intent","Source","Status","Phone","Address","User Email","Date"]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _set_offer_status(offer_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE offers SET status=? WHERE id=?", (status, offer_id))
    conn.commit()
    conn.close()


def _save_counter_price(offer_id, counter_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE offers SET counter_price=? WHERE id=?", (counter_price, offer_id))
    conn.commit()
    conn.close()


def _delete_offer(offer_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM offers WHERE id=?", (offer_id,))
    conn.commit()
    conn.close()


def _get_vendors():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors ORDER BY total_orders DESC")
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _filter_junk(df):
    junk = ["chess.com","github.com","instagram","facebook",
            "twitter","linkedin","discord","youtube","reddit"]
    mask = df["Vendor"].str.lower().apply(
        lambda v: not any(j in v for j in junk)
    )
    return df[mask & (df["Price"] > 0)]


def _fmt_status(s):
    return {"pending":"🟡 Pending","accepted":"🟢 Accepted",
            "rejected":"🔴 Rejected","counter":"🔵 Counter"}.get(s, s)


# ── main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown("## Admin Panel")
    st.markdown('<div class="danger-box">⚠ You are logged in as <b>Admin</b>. Changes here are live.</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Inventory", "📋 Offers & Actions",
        "🏢 Vendors", "📊 Analytics", "⚙ Run Pipeline"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Current Inventory")
        inv = load_inventory()

        if inv:
            rows = [{"Product": p.title(), "Stock (kg)": v.get("stock",0),
                     "Cost Price (₹/kg)": v.get("cost_price",0)} for p, v in inv.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            st.markdown('<div class="section-label">Update product</div>', unsafe_allow_html=True)
            sel = st.selectbox("Select", [p.title() for p in inv], key="upd_sel")
            sk  = sel.lower()
            c1, c2 = st.columns(2)
            with c1:
                ns = st.number_input("New stock (kg)", 0.0,
                                     value=float(inv[sk].get("stock",0)), step=50.0, key="upd_s")
            with c2:
                nc = st.number_input("New cost price (₹/kg)", 0.0,
                                     value=float(inv[sk].get("cost_price",0)), step=1.0, key="upd_c")
            if st.button("💾 Save", key="save_upd"):
                update_inventory({sk: {"stock": ns, "cost_price": nc}})
                st.markdown('<div class="success-box">✓ Updated.</div>', unsafe_allow_html=True)
                st.rerun()

            st.markdown('<div class="section-label">Remove product</div>', unsafe_allow_html=True)
            del_sel = st.selectbox("Product to remove", [p.title() for p in inv], key="del_sel")
            if st.checkbox(f"Confirm delete **{del_sel}**", key="del_chk"):
                if st.button("🗑 Delete", key="del_btn"):
                    _delete_product(del_sel.lower())
                    st.markdown('<div class="success-box">✓ Deleted.</div>', unsafe_allow_html=True)
                    st.rerun()

        st.markdown('<div class="section-label">Add new product</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: new_p = st.text_input("Name", placeholder="barley", key="add_n")
        with c2: add_s = st.number_input("Stock (kg)", 0.0, step=50.0, key="add_s")
        with c3: add_c = st.number_input("Cost price (₹/kg)", 0.0, step=1.0, key="add_c")
        if st.button("➕ Add", key="add_btn"):
            if not new_p.strip():
                st.warning("Enter a product name.")
            else:
                k = new_p.strip().lower()
                inv = load_inventory()
                if k in inv:
                    st.warning("Already exists.")
                else:
                    update_inventory({k: {"stock": add_s, "cost_price": add_c}})
                    st.markdown(f'<div class="success-box">✓ Added {new_p.title()}.</div>',
                                unsafe_allow_html=True)
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Offers & Actions (Accept / Counter / Reject)
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### All Offers")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: start = st.date_input("From date", key="of_start")
        with col2: end   = st.date_input("To date",   key="of_end")
        with col3: use_f = st.checkbox("Apply filter", key="of_chk")

        df = _get_offers(str(start), str(end)) if use_f else _get_offers()

        hide_junk = st.checkbox("Hide non-vendor rows", value=True, key="hide_junk")
        if hide_junk:
            df = _filter_junk(df)

        if df.empty:
            st.markdown('<div class="info-box">No offers found.</div>', unsafe_allow_html=True)
        else:
            display = df.copy()
            display["Status"] = display["Status"].apply(_fmt_status)
            # Add total price column — use counter_price if set, else offer price
            if "Counter Price" in display.columns:
                display["Total (₹)"] = display.apply(
                    lambda r: f"₹{r['Counter Price'] * r['Qty']:,.0f}"
                    if r.get("Counter Price") else f"₹{r['Price'] * r['Qty']:,.0f}", axis=1
                )
            else:
                display["Total (₹)"] = display.apply(
                    lambda r: f"₹{r['Price'] * r['Qty']:,.0f}", axis=1
                )
            st.dataframe(display, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ✉ Take Action on an Offer")
            st.markdown('<div class="info-box">Select an offer ID. Email sent to vendor/user. Accepted offers automatically deduct stock.</div>',
                        unsafe_allow_html=True)

            sel_id  = st.selectbox("Select Offer ID", df["ID"].tolist(), key="action_id")
            sel_row = df[df["ID"] == sel_id].iloc[0]

            # Info card
            total = sel_row["Price"] * sel_row["Qty"]
            st.markdown(f"""
            <div class="info-box">
            <b>Product:</b> {sel_row['Product'].title()} &nbsp;|&nbsp;
            <b>Qty:</b> {sel_row['Qty']} kg &nbsp;|&nbsp;
            <b>Price:</b> ₹{sel_row['Price']}/kg &nbsp;|&nbsp;
            <b>Total:</b> ₹{total:,.0f} &nbsp;|&nbsp;
            <b>Vendor:</b> {sel_row['Vendor']} &nbsp;|&nbsp;
            <b>Status:</b> {_fmt_status(sel_row['Status'])}<br>
            <b>Phone:</b> {sel_row['Phone'] or '—'} &nbsp;|&nbsp;
            <b>Address:</b> {sel_row['Address'] or '—'} &nbsp;|&nbsp;
            <b>Source:</b> {sel_row['Source']}
            </div>
            """, unsafe_allow_html=True)

            # Editable email
            vendor_email = st.text_input(
                "Vendor / User email (editable)",
                value=str(sel_row["User Email"] or sel_row["Vendor Email"] or ""),
                key="v_email"
            )

            # ── 3-way action ──────────────────────────────────────────────────
            action = st.radio(
                "Action", ["✅ Accept", "🔵 Counter Offer", "🔴 Reject"],
                horizontal=True, key="action_radio"
            )

            # ── ACCEPT ────────────────────────────────────────────────────────
            if action == "✅ Accept":
                st.markdown('<div class="success-box">Accepting will mark the offer as accepted, deduct the quantity from inventory, and notify the vendor/user by email.</div>',
                            unsafe_allow_html=True)

                if st.button("✅ Confirm Accept", key="confirm_accept"):
                    if not vendor_email:
                        st.markdown('<div class="danger-box">No email found. Enter it above.</div>',
                                    unsafe_allow_html=True)
                    else:
                        product  = sel_row["Product"].lower()
                        quantity = float(sel_row["Qty"])
                        price    = float(sel_row["Price"])

                        # Deduct from inventory
                        deducted = deduct_stock(product, quantity)

                        if not deducted:
                            st.markdown(
                                f'<div class="danger-box">⚠ Insufficient stock to fulfil '
                                f'{quantity} kg of {product.title()}. '
                                f'Update inventory first.</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            # Mark accepted in DB
                            _set_offer_status(sel_id, "accepted")

                            # Notify vendor (email-sourced) or web user
                            if sel_row["Source"] == "web" and sel_row["User Email"]:
                                notify_user_status(
                                    sel_row["User Email"], sel_row["Vendor"],
                                    product, quantity, price, "accepted"
                                )
                            else:
                                send_acceptance(
                                    vendor_email, sel_row["Vendor"],
                                    product, quantity, price
                                )

                            st.markdown(
                                f'<div class="success-box">✓ Offer accepted! '
                                f'<b>{quantity} kg</b> of <b>{product.title()}</b> '
                                f'deducted from inventory. Notification sent to '
                                f'<b>{vendor_email}</b>.</div>',
                                unsafe_allow_html=True
                            )
                            st.rerun()

            # ── COUNTER ───────────────────────────────────────────────────────
            elif action == "🔵 Counter Offer":
                c1, c2 = st.columns(2)
                with c1:
                    counter_price = st.number_input(
                        "Counter price (₹/kg)",
                        min_value=0.1,
                        value=float(sel_row["Price"]) * 0.95,
                        step=0.5, key="counter_p"
                    )
                with c2:
                    counter_note = st.text_input("Note (optional)", key="counter_note")

                if st.button("📤 Send Counter Offer", key="send_counter"):
                    if not vendor_email:
                        st.markdown('<div class="danger-box">No email found.</div>',
                                    unsafe_allow_html=True)
                    else:
                        ok = send_counter_offer(
                            vendor_email, sel_row["Vendor"],
                            sel_row["Product"], sel_row["Price"],
                            counter_price, sel_row["Qty"], counter_note
                        )
                        # Also notify web user if applicable
                        if sel_row["Source"] == "web" and sel_row["User Email"]:
                            notify_user_status(
                                sel_row["User Email"], sel_row["Vendor"],
                                sel_row["Product"], sel_row["Qty"],
                                sel_row["Price"], "counter",
                                counter_price=counter_price
                            )
                        if ok:
                            _set_offer_status(sel_id, "counter")
                            # save the counter price so user can see it
                            _save_counter_price(sel_id, counter_price)
                            st.markdown(
                                f'<div class="success-box">✓ Counter offer sent to '
                                f'{vendor_email}.</div>', unsafe_allow_html=True
                            )
                            st.rerun()
                        else:
                            st.markdown('<div class="danger-box">Failed to send. Check Gmail credentials.</div>',
                                        unsafe_allow_html=True)

            # ── REJECT ────────────────────────────────────────────────────────
            else:
                reason = st.text_input("Reason (optional)", key="rej_reason")

                if st.button("🚫 Send Rejection", key="send_reject"):
                    if not vendor_email:
                        st.markdown('<div class="danger-box">No email found.</div>',
                                    unsafe_allow_html=True)
                    else:
                        ok = send_rejection(vendor_email, sel_row["Vendor"],
                                            sel_row["Product"], reason)
                        if sel_row["Source"] == "web" and sel_row["User Email"]:
                            notify_user_status(
                                sel_row["User Email"], sel_row["Vendor"],
                                sel_row["Product"], sel_row["Qty"],
                                sel_row["Price"], "rejected", reason=reason
                            )
                        if ok:
                            _set_offer_status(sel_id, "rejected")
                            st.markdown(
                                f'<div class="success-box">✓ Rejection sent to '
                                f'{vendor_email}.</div>', unsafe_allow_html=True
                            )
                            st.rerun()
                        else:
                            st.markdown('<div class="danger-box">Failed to send. Check Gmail credentials.</div>',
                                        unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 🗑 Delete Offer")
            del_id = st.number_input("Offer ID", min_value=1, step=1, key="del_off")
            if st.button("Delete", key="del_off_btn"):
                _delete_offer(int(del_id))
                st.markdown(f'<div class="success-box">✓ Offer {del_id} deleted.</div>',
                            unsafe_allow_html=True)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Vendors
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### All Vendors")
        df_v = _get_vendors()
        if df_v.empty:
            st.markdown('<div class="info-box">No vendor data.</div>', unsafe_allow_html=True)
        else:
            st.dataframe(df_v, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Analytics
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        from frontend.analytics import render as render_analytics
        render_analytics()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 5 — Run Pipeline
    # ══════════════════════════════════════════════════════════════════════════
    with tab5:
        st.markdown("### Run Email Processing Pipeline")
        st.markdown('<div class="info-box">Fetches new emails from Gmail, extracts offers via Gemini, saves to DB.</div>',
                    unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: start_d = st.text_input("Start (YYYY/MM/DD)", "2024/01/01", key="pipe_s")
        with c2: end_d   = st.text_input("End   (YYYY/MM/DD)", "2026/12/31", key="pipe_e")

        if st.button("▶ Run Pipeline Now", key="run_pipe"):
            with st.spinner("Running pipeline..."):
                try:
                    from gmail.email_reader import fetch_emails
                    from ai.gemini_extractor import extract_offers_batch
                    from database.offer_history import save_offer
                    from processing.normalization import normalize_offer
                    from inventory.inventory_manager import get_available_stock
                    from gmail.email_sender import send_stock_exceeded_reply
                    from config.settings import AUTO_REPLY_ON_STOCK_EXCEEDED
                    import main as m

                    JUNK = ["chess.com","github","instagram","facebook",
                            "twitter","linkedin","discord","youtube","tiktok"]

                    all_emails = fetch_emails(start_d, end_d)
                    saved = skipped = exceeded = 0

                    valid_emails = []
                    for email in all_emails:
                        sender = email["sender"]
                        if m.is_automated_email(sender) or m.is_admin_email(sender):
                            skipped += 1
                        else:
                            email["sender_email"] = m.extract_email_address(sender)
                            valid_emails.append(email)

                    st.info(f"Fetched {len(all_emails)} — {len(valid_emails)} valid, {skipped} skipped.")

                    if not valid_emails:
                        st.markdown('<div class="info-box">No valid emails.</div>',
                                    unsafe_allow_html=True)
                    else:
                        offers = extract_offers_batch(valid_emails)

                        for offer in offers:
                            offer = normalize_offer(offer)
                            if any(j in offer.get("vendor","").lower() for j in JUNK):
                                skipped += 1
                                continue

                            qty   = offer.get("quantity") or 0
                            prod  = offer.get("product")
                            avail = get_available_stock(prod)

                            if qty > avail:
                                exceeded += 1
                                if AUTO_REPLY_ON_STOCK_EXCEEDED:
                                    ve = offer.get("vendor_email","")
                                    if ve:
                                        send_stock_exceeded_reply(
                                            ve, offer.get("vendor",""), prod, qty, avail)
                                continue

                            try:
                                save_offer(offer)
                                saved += 1
                            except Exception:
                                skipped += 1

                        st.markdown(
                            f'<div class="success-box">✓ Done — <b>1 Gemini call</b> · '
                            f'<b>{saved}</b> saved · <b>{exceeded}</b> exceeded stock · '
                            f'<b>{skipped}</b> skipped.</div>',
                            unsafe_allow_html=True
                        )

                except RuntimeError as e:
                    st.markdown(
                        f'<div class="danger-box">{e}<br><br>'
                        f'Add <code>GOOGLE_TOKEN_B64</code> to Streamlit secrets.</div>',
                        unsafe_allow_html=True
                    )
                except Exception as e:
                    st.markdown(f'<div class="danger-box">Pipeline error: {e}</div>',
                                unsafe_allow_html=True)