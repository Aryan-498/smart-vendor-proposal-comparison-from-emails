"""
Admin Dashboard — only accessible to the ADMIN_EMAIL account.
Features:
  • Add new product to inventory
  • Update stock / cost_price for existing product
  • Remove a product entirely
  • View all raw DB tables
  • Trigger email processing manually
"""

import json
import pandas as pd
import streamlit as st

from inventory.inventory_manager import (
    load_inventory,
    update_inventory,
    save_inventory,
    reload_inventory,
)
from database.db_manager import get_connection
from config.settings import INVENTORY_PATH
import os


# ── helpers ───────────────────────────────────────────────────────────────────

def _delete_product(product: str):
    inv = load_inventory()
    if product in inv:
        del inv[product]
        save_inventory(inv)
        reload_inventory()
        return True
    return False


def _all_offers_df():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM offers ORDER BY id DESC LIMIT 200")
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _all_vendors_df():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vendors ORDER BY total_orders DESC")
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _delete_offer(offer_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
    conn.commit()
    conn.close()


# ── main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown("## Admin Panel")
    st.markdown('<div class="danger-box">⚠ You are logged in as <b>Admin</b>. Changes here directly affect live inventory and the database.</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📦 Inventory", "📋 Offers DB", "🏢 Vendors DB", "⚙ Run Pipeline"])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory Management
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Current Inventory")
        inv = load_inventory()

        if not inv:
            st.markdown('<div class="info-box">Inventory is empty. Add the first product below.</div>', unsafe_allow_html=True)
        else:
            inv_rows = [
                {
                    "Product":        p.title(),
                    "Stock (kg)":     v.get("stock", 0),
                    "Cost Price (₹)": v.get("cost_price", 0),
                }
                for p, v in inv.items()
            ]
            st.dataframe(pd.DataFrame(inv_rows), use_container_width=True, hide_index=True)

        # ── Update existing product ───────────────────────────────────────────
        if inv:
            st.markdown('<div class="section-label">Update existing product</div>', unsafe_allow_html=True)

            product_list = list(inv.keys())
            sel = st.selectbox("Select product to update", [p.title() for p in product_list], key="upd_sel")
            sel_key = sel.lower()

            col1, col2 = st.columns(2)
            with col1:
                new_stock = st.number_input(
                    "New stock (kg)",
                    min_value=0.0,
                    value=float(inv[sel_key].get("stock", 0)),
                    step=50.0,
                    key="upd_stock"
                )
            with col2:
                new_cost = st.number_input(
                    "New cost price (₹/kg)",
                    min_value=0.0,
                    value=float(inv[sel_key].get("cost_price", 0)),
                    step=1.0,
                    key="upd_cost"
                )

            if st.button("💾 Save Updates", key="save_upd"):
                applied = update_inventory({sel_key: {"stock": new_stock, "cost_price": new_cost}})
                if applied:
                    st.markdown(f'<div class="success-box">✓ Updated <b>{sel}</b>: stock={new_stock} kg, cost_price=₹{new_cost}/kg</div>', unsafe_allow_html=True)
                    st.rerun()

            # ── Delete product ────────────────────────────────────────────────
            st.markdown('<div class="section-label">Remove product</div>', unsafe_allow_html=True)
            del_sel = st.selectbox("Select product to remove", [p.title() for p in product_list], key="del_sel")

            confirm = st.checkbox(f"I confirm I want to permanently delete **{del_sel}** from inventory")

            if confirm:
                if st.button("🗑 Delete Product", key="del_btn"):
                    if _delete_product(del_sel.lower()):
                        st.markdown(f'<div class="success-box">✓ <b>{del_sel}</b> removed from inventory.</div>', unsafe_allow_html=True)
                        st.rerun()

        # ── Add new product ───────────────────────────────────────────────────
        st.markdown('<div class="section-label">Add new product</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            new_product = st.text_input("Product name", placeholder="e.g. barley", key="add_name")
        with col2:
            add_stock = st.number_input("Initial stock (kg)", min_value=0.0, step=50.0, key="add_stock")
        with col3:
            add_cost = st.number_input("Cost price (₹/kg)", min_value=0.0, step=1.0, key="add_cost")

        if st.button("➕ Add Product", key="add_btn"):
            if not new_product.strip():
                st.warning("Please enter a product name.")
            else:
                key = new_product.strip().lower()
                inv = load_inventory()
                if key in inv:
                    st.warning(f"'{new_product}' already exists. Use the update form above.")
                else:
                    applied = update_inventory({key: {"stock": add_stock, "cost_price": add_cost}})
                    if applied:
                        st.markdown(f'<div class="success-box">✓ Added <b>{new_product.title()}</b> — stock={add_stock} kg, cost_price=₹{add_cost}/kg</div>', unsafe_allow_html=True)
                        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Offers Database
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### All Offers (latest 200)")
        df = _all_offers_df()

        if df.empty:
            st.markdown('<div class="info-box">No offers in the database.</div>', unsafe_allow_html=True)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.markdown('<div class="section-label">Delete an offer by ID</div>', unsafe_allow_html=True)
            del_id = st.number_input("Offer ID to delete", min_value=1, step=1, key="del_offer_id")
            if st.button("🗑 Delete Offer", key="del_offer_btn"):
                _delete_offer(int(del_id))
                st.markdown(f'<div class="success-box">✓ Offer ID {del_id} deleted.</div>', unsafe_allow_html=True)
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Vendors Database
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### All Vendors")
        df_v = _all_vendors_df()

        if df_v.empty:
            st.markdown('<div class="info-box">No vendor data yet.</div>', unsafe_allow_html=True)
        else:
            st.dataframe(df_v, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Run Pipeline
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown("### Run Email Processing Pipeline")
        st.markdown('<div class="info-box">This will fetch new emails from Gmail, extract offers using Gemini, and save them to the database. Only unprocessed emails will be fetched.</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.text_input("Start date (YYYY/MM/DD)", value="2024/01/01")
        with col2:
            end_date = st.text_input("End date (YYYY/MM/DD)", value="2026/12/31")

        if st.button("▶ Run Pipeline Now", key="run_pipeline"):
            with st.spinner("Running... this may take a minute."):
                try:
                    from gmail.email_reader import fetch_emails
                    from ai.gemini_extractor import extract_offer
                    from database.offer_history import save_offer
                    from processing.normalization import normalize_offer
                    from inventory.inventory_manager import get_available_stock
                    from gmail.email_sender import send_stock_exceeded_reply
                    from config.settings import AUTO_REPLY_ON_STOCK_EXCEEDED
                    import main as m

                    # Patch dates and run
                    emails = fetch_emails(start_date, end_date)
                    saved, skipped, exceeded = 0, 0, 0

                    for email in emails:
                        sender  = email["sender"]
                        body    = email["body"]
                        subject = email.get("subject", "")

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

                            qty  = offer.get("quantity") or 0
                            prod = offer.get("product")
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

                    st.markdown(f'<div class="success-box">✓ Pipeline complete — <b>{saved}</b> offers saved, <b>{exceeded}</b> exceeded stock (auto-replied), <b>{skipped}</b> skipped.</div>', unsafe_allow_html=True)

                except Exception as e:
                    st.markdown(f'<div class="danger-box">Pipeline error: {e}</div>', unsafe_allow_html=True)