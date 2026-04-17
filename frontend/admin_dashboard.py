"""
Admin Dashboard — ADMIN_EMAIL only.
Tabs:
  1. Inventory — add / update / delete products
  2. Offers DB — view all, filter by date, counter-offer, reject, delete
  3. Vendors DB — view
  4. Run Pipeline — fetch emails from Gmail
"""

import json, os
import pandas as pd
import streamlit as st

from inventory.inventory_manager import (
    load_inventory, update_inventory, save_inventory, reload_inventory
)
from database.db_manager import get_connection
from gmail.email_sender import send_counter_offer, send_rejection


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
                   intent, source, status, email_date
            FROM offers
            WHERE date(email_date) BETWEEN date(?) AND date(?)
            ORDER BY id DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, product, quantity, unit, price, vendor, vendor_email,
                   intent, source, status, email_date
            FROM offers ORDER BY id DESC LIMIT 300
        """)
    rows = cursor.fetchall()
    cols = ["ID","Product","Qty","Unit","Price","Vendor","Vendor Email",
            "Intent","Source","Status","Date"]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _set_offer_status(offer_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE offers SET status=? WHERE id=?", (status, offer_id))
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


def _filter_chess_and_junk(df):
    """Remove clearly non-vendor rows (chess.com, price=0, etc.)"""
    junk_vendors = ["chess.com", "github.com", "instagram", "facebook",
                    "twitter", "linkedin", "discord", "youtube", "reddit"]
    mask = df["Vendor"].str.lower().apply(
        lambda v: not any(j in v for j in junk_vendors)
    )
    return df[mask & (df["Price"] > 0)]


# ── main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown("## Admin Panel")
    st.markdown('<div class="danger-box">⚠ You are logged in as <b>Admin</b>. Changes here are live.</div>',
                unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "📋 Offers & Actions", "🏢 Vendors", "⚙ Run Pipeline"])

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

            # Update
            st.markdown('<div class="section-label">Update product</div>', unsafe_allow_html=True)
            sel = st.selectbox("Select", [p.title() for p in inv], key="upd_sel")
            sk  = sel.lower()
            c1, c2 = st.columns(2)
            with c1:
                ns = st.number_input("New stock (kg)", 0.0, value=float(inv[sk].get("stock",0)), step=50.0, key="upd_s")
            with c2:
                nc = st.number_input("New cost price (₹/kg)", 0.0, value=float(inv[sk].get("cost_price",0)), step=1.0, key="upd_c")
            if st.button("💾 Save", key="save_upd"):
                update_inventory({sk: {"stock": ns, "cost_price": nc}})
                st.markdown('<div class="success-box">✓ Updated.</div>', unsafe_allow_html=True)
                st.rerun()

            # Delete
            st.markdown('<div class="section-label">Remove product</div>', unsafe_allow_html=True)
            del_sel = st.selectbox("Product to remove", [p.title() for p in inv], key="del_sel")
            if st.checkbox(f"Confirm delete **{del_sel}**", key="del_chk"):
                if st.button("🗑 Delete", key="del_btn"):
                    _delete_product(del_sel.lower())
                    st.markdown('<div class="success-box">✓ Deleted.</div>', unsafe_allow_html=True)
                    st.rerun()

        # Add new
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
                    st.markdown(f'<div class="success-box">✓ Added {new_p.title()}.</div>', unsafe_allow_html=True)
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Offers + Counter / Reject actions
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### All Offers")

        # Date filter
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            start = st.date_input("From date", key="of_start")
        with col2:
            end   = st.date_input("To date", key="of_end")
        with col3:
            use_filter = st.checkbox("Apply filter", key="of_chk")

        if use_filter:
            df = _get_offers(str(start), str(end))
        else:
            df = _get_offers()

        # Toggle junk filter
        hide_junk = st.checkbox("Hide non-vendor rows (Chess.com, price=0, etc.)", value=True, key="hide_junk")
        if hide_junk:
            df = _filter_chess_and_junk(df)

        if df.empty:
            st.markdown('<div class="info-box">No offers found.</div>', unsafe_allow_html=True)
        else:
            # Status color
            def fmt_status(s):
                return {"pending":"🟡 Pending","accepted":"🟢 Accepted",
                        "rejected":"🔴 Rejected","counter":"🔵 Counter"}.get(s, s)
            display_df = df.copy()
            display_df["Status"] = display_df["Status"].apply(fmt_status)
            st.dataframe(display_df, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### ✉ Send Counter Offer or Rejection")
            st.markdown('<div class="info-box">Select an offer ID from the table above. The email will be sent to the vendor\'s email address.</div>', unsafe_allow_html=True)

            offer_ids = df["ID"].tolist()
            sel_id = st.selectbox("Select Offer ID", offer_ids, key="action_id")

            sel_row = df[df["ID"] == sel_id].iloc[0]
            st.markdown(f"""
            <div class="info-box">
            <b>Product:</b> {sel_row['Product'].title()} &nbsp;|&nbsp;
            <b>Qty:</b> {sel_row['Qty']} kg &nbsp;|&nbsp;
            <b>Price:</b> ₹{sel_row['Price']}/kg &nbsp;|&nbsp;
            <b>Vendor:</b> {sel_row['Vendor']} &nbsp;|&nbsp;
            <b>Email:</b> {sel_row['Vendor Email'] or '(no email on file)'}
            </div>
            """, unsafe_allow_html=True)

            vendor_email_override = st.text_input(
                "Vendor email (editable)",
                value=str(sel_row["Vendor Email"]) if sel_row["Vendor Email"] else "",
                key="v_email"
            )

            action = st.radio("Action", ["Counter Offer", "Reject"], horizontal=True, key="action_radio")

            if action == "Counter Offer":
                c1, c2 = st.columns(2)
                with c1:
                    counter_price = st.number_input(
                        "Your counter price (₹/kg)",
                        min_value=0.1,
                        value=float(sel_row["Price"]) * 0.95,
                        step=0.5,
                        key="counter_p"
                    )
                with c2:
                    counter_note = st.text_input("Note (optional)", key="counter_note")

                if st.button("📤 Send Counter Offer", key="send_counter"):
                    if not vendor_email_override:
                        st.markdown('<div class="danger-box">No vendor email found. Enter it above.</div>', unsafe_allow_html=True)
                    else:
                        ok = send_counter_offer(
                            vendor_email=vendor_email_override,
                            vendor_name=sel_row["Vendor"],
                            product=sel_row["Product"],
                            original_price=sel_row["Price"],
                            counter_price=counter_price,
                            quantity=sel_row["Qty"],
                            note=counter_note
                        )
                        if ok:
                            _set_offer_status(sel_id, "counter")
                            st.markdown(f'<div class="success-box">✓ Counter offer sent to {vendor_email_override}. Offer marked as Counter.</div>', unsafe_allow_html=True)
                            st.rerun()
                        else:
                            st.markdown('<div class="danger-box">Failed to send email. Check Gmail credentials.</div>', unsafe_allow_html=True)

            else:  # Reject
                reason = st.text_input("Reason for rejection (optional)", key="rej_reason")

                if st.button("🚫 Send Rejection", key="send_reject"):
                    if not vendor_email_override:
                        st.markdown('<div class="danger-box">No vendor email found. Enter it above.</div>', unsafe_allow_html=True)
                    else:
                        ok = send_rejection(
                            vendor_email=vendor_email_override,
                            vendor_name=sel_row["Vendor"],
                            product=sel_row["Product"],
                            reason=reason
                        )
                        if ok:
                            _set_offer_status(sel_id, "rejected")
                            st.markdown(f'<div class="success-box">✓ Rejection sent to {vendor_email_override}. Offer marked as Rejected.</div>', unsafe_allow_html=True)
                            st.rerun()
                        else:
                            st.markdown('<div class="danger-box">Failed to send email. Check Gmail credentials.</div>', unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 🗑 Delete Offer")
            del_id = st.number_input("Offer ID to delete", min_value=1, step=1, key="del_off")
            if st.button("Delete", key="del_off_btn"):
                _delete_offer(int(del_id))
                st.markdown(f'<div class="success-box">✓ Offer {del_id} deleted.</div>', unsafe_allow_html=True)
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
    # TAB 4 — Run Pipeline
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### Run Email Processing Pipeline")
        st.markdown('<div class="info-box">Fetches new emails from Gmail, extracts offers via Gemini, saves to DB. Requires Gmail credentials to be configured in secrets.</div>', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: start_d = st.text_input("Start (YYYY/MM/DD)", "2024/01/01", key="pipe_s")
        with c2: end_d   = st.text_input("End   (YYYY/MM/DD)", "2026/12/31", key="pipe_e")

        if st.button("▶ Run Pipeline Now", key="run_pipe"):
            with st.spinner("Running pipeline..."):
                try:
                    from gmail.email_reader import fetch_emails
                    from ai.gemini_extractor import extract_offer
                    from database.offer_history import save_offer
                    from processing.normalization import normalize_offer
                    from inventory.inventory_manager import get_available_stock
                    from gmail.email_sender import send_stock_exceeded_reply
                    from config.settings import AUTO_REPLY_ON_STOCK_EXCEEDED
                    import main as m

                    emails = fetch_emails(start_d, end_d)
                    saved = skipped = exceeded = 0

                    for email in emails:
                        sender  = email["sender"]
                        body    = email["body"]

                        if m.is_automated_email(sender) or m.is_admin_email(sender):
                            skipped += 1
                            continue

                        offers = extract_offer(body)
                        if not offers:
                            skipped += 1
                            continue

                        for offer in offers:
                            if not offer.get("vendor"):
                                offer["vendor"] = sender.split("<")[0].strip()
                            offer = normalize_offer(offer)

                            # skip junk (chess.com etc.)
                            vendor_l = offer.get("vendor","").lower()
                            if any(j in vendor_l for j in ["chess.com","github","instagram","facebook","twitter"]):
                                skipped += 1
                                continue

                            qty   = offer.get("quantity") or 0
                            prod  = offer.get("product")
                            avail = get_available_stock(prod)

                            if qty > avail:
                                exceeded += 1
                                if AUTO_REPLY_ON_STOCK_EXCEEDED:
                                    ve = m.extract_email_address(sender)
                                    send_stock_exceeded_reply(ve, ve, prod, qty, avail)
                                continue

                            try:
                                save_offer(offer)
                                saved += 1
                            except Exception:
                                skipped += 1

                    st.markdown(
                        f'<div class="success-box">✓ Done — <b>{saved}</b> saved, '
                        f'<b>{exceeded}</b> exceeded stock, <b>{skipped}</b> skipped.</div>',
                        unsafe_allow_html=True
                    )

                except RuntimeError as e:
                    st.markdown(f'<div class="danger-box">{e}<br><br>'
                                f'<b>How to fix:</b> Run locally first, then run:<br>'
                                f'<code>cat config/token.json | base64</code><br>'
                                f'Copy the output and add it to Streamlit secrets as '
                                f'<code>GOOGLE_TOKEN_B64 = "..."</code></div>',
                                unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="danger-box">Pipeline error: {e}</div>', unsafe_allow_html=True)