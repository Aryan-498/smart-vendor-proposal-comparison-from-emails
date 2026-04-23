"""
Admin Dashboard — ADMIN_EMAIL only.
Tabs: Inventory | Offers & Actions | Vendors & Blacklist | Analytics | Run Pipeline
"""

import io
import pandas as pd
import streamlit as st

from inventory.inventory_manager import (
    load_inventory, update_inventory, save_inventory,
    reload_inventory, deduct_stock, check_low_stock_alerts
)
from database.db_manager import (
    get_connection, create_tables,
    is_blacklisted, add_to_blacklist, remove_from_blacklist, get_blacklist
)
from gmail.email_sender import (
    send_counter_offer, send_rejection, send_acceptance,
    notify_user_status, send_low_stock_alert
)
from config.settings import ADMIN_EMAIL


# ── cached read helpers ───────────────────────────────────────────────────────

@st.cache_data(ttl=30, show_spinner=False)
def _cached_offers(start_date=None, end_date=None):
    """Cache offer table reads — 30s TTL."""
    return _get_offers(start_date, end_date)


@st.cache_data(ttl=30, show_spinner=False)
def _cached_vendors():
    """Cache vendor table reads."""
    return _get_vendors()


@st.cache_data(ttl=30, show_spinner=False)
def _cached_blacklist():
    """Cache blacklist reads."""
    return get_blacklist()


@st.cache_data(ttl=30, show_spinner=False)
def _cached_inventory():
    """Cache inventory reads."""
    return load_inventory()


@st.cache_data(ttl=30, show_spinner=False)
def _cached_low_stock():
    """Cache low stock check."""
    return check_low_stock_alerts()


@st.cache_data(ttl=30, show_spinner=False)
def _cached_price_history():
    """Cache price history reads."""
    return _price_history()


def _invalidate_admin_cache():
    """Clear all admin caches after any write."""
    _cached_offers.clear()
    _cached_vendors.clear()
    _cached_blacklist.clear()
    _cached_inventory.clear()
    _cached_low_stock.clear()
    _cached_price_history.clear()


# ── helpers ───────────────────────────────────────────────────────────────────

def _get_offers(start_date=None, end_date=None):
    create_tables()
    conn = get_connection()
    cursor = conn.cursor()
    if start_date and end_date:
        cursor.execute("""
            SELECT id, product, quantity, unit, price, vendor, vendor_email,
                   intent, source, status, phone, address, user_email,
                   counter_price, user_counter_price, email_date
            FROM offers
            WHERE date(email_date) BETWEEN date(?) AND date(?)
            ORDER BY id DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
            SELECT id, product, quantity, unit, price, vendor, vendor_email,
                   intent, source, status, phone, address, user_email,
                   counter_price, user_counter_price, email_date
            FROM offers ORDER BY id DESC LIMIT 500
        """)
    rows   = cursor.fetchall()
    cols   = ["ID","Product","Qty","Unit","Price","Vendor","Vendor Email",
              "Intent","Source","Status","Phone","Address","User Email",
              "Counter Price","User Counter","Date"]
    conn.close()
    return pd.DataFrame(rows, columns=cols)


def _set_status(offer_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE offers SET status=? WHERE id=?", (status, offer_id))
    conn.commit()
    conn.close()


def _set_status_bulk(ids: list, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.executemany("UPDATE offers SET status=? WHERE id=?",
                       [(status, i) for i in ids])
    conn.commit()
    conn.close()


def _save_counter_price(offer_id, counter_price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE offers SET counter_price=? WHERE id=?",
                   (counter_price, offer_id))
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
        lambda v: not any(j in v for j in junk))
    return df[mask & (df["Price"] > 0)]


def _fmt_status(s):
    return {"pending":"🟡 Pending","accepted":"🟢 Accepted",
            "rejected":"🔴 Rejected","counter":"🔵 Counter",
            "counter_declined":"⚫ User Declined",
            "user_counter":"🔄 User Counter"}.get(s, s)


def _price_history():
    """Accepted offers grouped by week for price history chart."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT product, price, email_date FROM offers
        WHERE status='accepted' AND price > 0
        ORDER BY email_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["Product","Price","Date"])
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    df["Week"] = df["Date"].dt.to_period("W").dt.start_time
    return df


# ── main render ───────────────────────────────────────────────────────────────

def render():
    st.markdown("## Admin Panel")
    st.markdown('<div class="danger-box">⚠ You are logged in as <b>Admin</b>. Changes here are live.</div>',
                unsafe_allow_html=True)

    # Low stock alert banner
    alerts = _cached_low_stock()
    if alerts:
        names = ", ".join(a["product"].title() for a in alerts)
        st.markdown(
            f'<div class="danger-box">⚠ <b>Low Stock:</b> {names} — '
            f'<a href="#" style="color:inherit;">check Inventory tab</a></div>',
            unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 Inventory", "📋 Offers & Actions",
        "🏢 Vendors & Blacklist", "📊 Analytics", "⚙ Run Pipeline"
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Inventory (with min order + low stock threshold)
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Current Inventory")
        inv = _cached_inventory()

        if inv:
            rows = [{"Product": p.title(),
                     "Stock (kg)":   v.get("stock", 0),
                     "Cost Price":   f"₹{v.get('cost_price',0)}/kg",
                     "Min Order":    f"{v.get('min_order',1)} kg",
                     "Alert Below":  f"{v.get('low_stock_threshold',100)} kg",
                     "Status":       "🟢 OK" if v.get("stock",0) >= v.get("low_stock_threshold",100) else "🔴 Low"}
                    for p, v in inv.items()]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            # Send low stock alert email
            if alerts and st.button("📧 Email Low Stock Alert to Admin", key="send_alert"):
                send_low_stock_alert(ADMIN_EMAIL, alerts)
                st.markdown('<div class="success-box">✓ Alert sent.</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-label">Update product</div>', unsafe_allow_html=True)
            sel = st.selectbox("Select", [p.title() for p in inv], key="upd_sel")
            sk  = sel.lower()
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                ns = st.number_input("Stock (kg)", 0.0, value=float(inv[sk].get("stock",0)), step=50.0, key="upd_s")
            with c2:
                nc = st.number_input("Cost price (₹/kg)", 0.0, value=float(inv[sk].get("cost_price",0)), step=1.0, key="upd_c")
            with c3:
                nm = st.number_input("Min order (kg)", 0.0, value=float(inv[sk].get("min_order",1)), step=10.0, key="upd_m")
            with c4:
                nt = st.number_input("Alert below (kg)", 0.0, value=float(inv[sk].get("low_stock_threshold",100)), step=10.0, key="upd_t")
            if st.button("💾 Save", key="save_upd"):
                update_inventory({sk: {"stock": ns, "cost_price": nc,
                                       "min_order": nm, "low_stock_threshold": nt}})
                _invalidate_admin_cache()
                st.markdown('<div class="success-box">✓ Updated.</div>', unsafe_allow_html=True)
                st.rerun()

            st.markdown('<div class="section-label">Remove product</div>', unsafe_allow_html=True)
            del_sel = st.selectbox("Product to remove", [p.title() for p in inv], key="del_sel")
            if st.checkbox(f"Confirm delete **{del_sel}**", key="del_chk"):
                if st.button("🗑 Delete", key="del_btn"):
                    inv = load_inventory()
                    del inv[del_sel.lower()]
                    save_inventory(inv)
                    reload_inventory()
                    st.rerun()

        st.markdown('<div class="section-label">Add new product</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: new_p = st.text_input("Name", placeholder="barley", key="add_n")
        with c2: add_s = st.number_input("Stock (kg)", 0.0, step=50.0, key="add_s")
        with c3: add_c = st.number_input("Cost (₹/kg)", 0.0, step=1.0, key="add_c")
        with c4: add_m = st.number_input("Min order (kg)", 1.0, step=10.0, key="add_m")
        with c5: add_t = st.number_input("Alert below (kg)", 100.0, step=10.0, key="add_t")
        if st.button("➕ Add", key="add_btn"):
            if not new_p.strip():
                st.warning("Enter a product name.")
            else:
                k = new_p.strip().lower()
                if k in load_inventory():
                    st.warning("Already exists.")
                else:
                    update_inventory({k: {"stock": add_s, "cost_price": add_c,
                                          "min_order": add_m, "low_stock_threshold": add_t}})
                    _invalidate_admin_cache()
                    st.markdown(f'<div class="success-box">✓ Added {new_p.title()}.</div>',
                                unsafe_allow_html=True)
                    st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Offers & Actions (bulk + single + export)
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### All Offers")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1: start = st.date_input("From", key="of_start")
        with col2: end   = st.date_input("To",   key="of_end")
        with col3: use_f = st.checkbox("Apply", key="of_chk")

        df = _get_offers(str(start), str(end)) if use_f else _get_offers()

        hide_junk = st.checkbox("Hide non-vendor rows", value=True, key="hide_junk")
        if hide_junk:
            df = _filter_junk(df)

        if df.empty:
            st.markdown('<div class="info-box">No offers found.</div>', unsafe_allow_html=True)
        else:
            display = df.copy()
            display["Status"] = display["Status"].apply(_fmt_status)
            display["Total (₹)"] = display.apply(
                lambda r: f"₹{r['Price'] * r['Qty']:,.0f}", axis=1)
            st.dataframe(display, use_container_width=True, hide_index=True)

            # ── Excel Export ──────────────────────────────────────────────────
            st.markdown('<div class="section-label">Export</div>', unsafe_allow_html=True)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                display.drop(columns=["ID"], errors="ignore").to_excel(
                    writer, index=False, sheet_name="Offers")
            st.download_button(
                "📥 Download as Excel",
                data=buf.getvalue(),
                file_name="vendoriq_offers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="dl_excel"
            )

            st.markdown("---")

            # ── Bulk Actions ──────────────────────────────────────────────────
            st.markdown("### ⚡ Bulk Actions")
            st.markdown('<div class="info-box">Select multiple offer IDs and apply an action to all at once.</div>',
                        unsafe_allow_html=True)

            pending_df = df[df["Status"].isin(["pending","counter","user_counter"])]
            if not pending_df.empty:
                bulk_ids = st.multiselect(
                    "Select Offer IDs",
                    options=pending_df["ID"].tolist(),
                    format_func=lambda i: f"#{i} — {df[df['ID']==i]['Product'].values[0].title()} "
                                          f"({df[df['ID']==i]['Vendor'].values[0]}) "
                                          f"₹{df[df['ID']==i]['Price'].values[0]}/kg",
                    key="bulk_ids"
                )

                if bulk_ids:
                    bulk_action = st.radio("Action for all selected",
                                           ["✅ Accept All", "🔴 Reject All"],
                                           horizontal=True, key="bulk_action")
                    bulk_reason = ""
                    if "Reject" in bulk_action:
                        bulk_reason = st.text_input("Rejection reason (optional)", key="bulk_reason")

                    if st.button("⚡ Apply to All Selected", key="bulk_apply"):
                        done = 0
                        for bid in bulk_ids:
                            row = df[df["ID"] == bid].iloc[0]
                            ve  = str(row["User Email"] or row["Vendor Email"] or "")
                            if "Accept" in bulk_action:
                                deducted = deduct_stock(row["Product"].lower(), row["Qty"])
                                if deducted:
                                    _set_status(bid, "accepted")
                                    if ve:
                                        try:
                                            if row["Source"] == "web":
                                                notify_user_status(ve, row["Vendor"], row["Product"],
                                                                   row["Qty"], row["Price"], "accepted")
                                            else:
                                                send_acceptance(ve, row["Vendor"], row["Product"],
                                                                row["Qty"], row["Price"])
                                        except Exception:
                                            pass
                                    done += 1
                            else:
                                _set_status(bid, "rejected")
                                if ve:
                                    try:
                                        notify_user_status(ve, row["Vendor"], row["Product"],
                                                           row["Qty"], row["Price"],
                                                           "rejected", reason=bulk_reason)
                                    except Exception:
                                        pass
                                done += 1

                        st.markdown(
                            f'<div class="success-box">✓ Action applied to <b>{done}</b> of '
                            f'<b>{len(bulk_ids)}</b> offers.</div>',
                            unsafe_allow_html=True)
                        st.rerun()
            else:
                st.markdown('<div class="info-box">No pending offers available for bulk action.</div>',
                            unsafe_allow_html=True)

            st.markdown("---")

            # ── Single Offer Action ───────────────────────────────────────────
            st.markdown("### ✉ Act on Single Offer")

            sel_id  = st.selectbox("Offer ID", df["ID"].tolist(), key="action_id")
            sel_row = df[df["ID"] == sel_id].iloc[0]
            total   = sel_row["Price"] * sel_row["Qty"]

            st.markdown(f"""
            <div class="info-box">
            <b>Product:</b> {sel_row['Product'].title()} &nbsp;|&nbsp;
            <b>Qty:</b> {sel_row['Qty']} kg &nbsp;|&nbsp;
            <b>Price:</b> ₹{sel_row['Price']}/kg &nbsp;|&nbsp;
            <b>Total:</b> ₹{total:,.0f}<br>
            <b>Vendor:</b> {sel_row['Vendor']} &nbsp;|&nbsp;
            <b>Status:</b> {_fmt_status(sel_row['Status'])} &nbsp;|&nbsp;
            <b>Phone:</b> {sel_row['Phone'] or '—'}<br>
            <b>User Counter:</b> {"₹" + str(sel_row['User Counter']) + "/kg" if sel_row['User Counter'] and sel_row['User Counter'] != "—" else "—"}
            </div>
            """, unsafe_allow_html=True)

            vendor_email = st.text_input(
                "Email (editable)",
                value=str(sel_row["User Email"] or sel_row["Vendor Email"] or ""),
                key="v_email")

            action = st.radio("Action", ["✅ Accept", "🔵 Counter Offer", "🔴 Reject"],
                              horizontal=True, key="action_radio")

            if action == "✅ Accept":
                if st.button("✅ Confirm Accept", key="confirm_accept"):
                    deducted = deduct_stock(sel_row["Product"].lower(), sel_row["Qty"])
                    if not deducted:
                        st.markdown('<div class="danger-box">⚠ Insufficient stock.</div>',
                                    unsafe_allow_html=True)
                    else:
                        _set_status(sel_id, "accepted")
                        _invalidate_admin_cache()
                        if vendor_email:
                            try:
                                if sel_row["Source"] == "web":
                                    notify_user_status(vendor_email, sel_row["Vendor"],
                                                       sel_row["Product"], sel_row["Qty"],
                                                       sel_row["Price"], "accepted")
                                else:
                                    send_acceptance(vendor_email, sel_row["Vendor"],
                                                    sel_row["Product"], sel_row["Qty"],
                                                    sel_row["Price"])
                            except Exception:
                                pass
                        st.markdown(
                            f'<div class="success-box">✓ Accepted. '
                            f'{sel_row["Qty"]} kg deducted from inventory.</div>',
                            unsafe_allow_html=True)
                        st.rerun()

            elif action == "🔵 Counter Offer":
                c1, c2 = st.columns(2)
                with c1:
                    cp = st.number_input("Counter price (₹/kg)",
                                         value=float(sel_row["Price"]) * 0.95,
                                         step=0.5, key="counter_p")
                with c2:
                    cn = st.text_input("Note", key="counter_note")
                st.caption(f"Counter total: ₹{cp * sel_row['Qty']:,.0f}")
                if st.button("📤 Send Counter", key="send_counter"):
                    ok = send_counter_offer(vendor_email, sel_row["Vendor"],
                                            sel_row["Product"], sel_row["Price"],
                                            cp, sel_row["Qty"], cn)
                    if sel_row["Source"] == "web" and sel_row["User Email"]:
                        try:
                            notify_user_status(sel_row["User Email"], sel_row["Vendor"],
                                               sel_row["Product"], sel_row["Qty"],
                                               sel_row["Price"], "counter", counter_price=cp)
                        except Exception:
                            pass
                    if ok:
                        _set_status(sel_id, "counter")
                        _invalidate_admin_cache()
                        _save_counter_price(sel_id, cp)
                        st.markdown(f'<div class="success-box">✓ Counter sent.</div>',
                                    unsafe_allow_html=True)
                        st.rerun()

            else:
                reason = st.text_input("Reason", key="rej_reason")
                if st.button("🚫 Reject", key="send_reject"):
                    send_rejection(vendor_email, sel_row["Vendor"],
                                   sel_row["Product"], reason)
                    if sel_row["Source"] == "web" and sel_row["User Email"]:
                        try:
                            notify_user_status(sel_row["User Email"], sel_row["Vendor"],
                                               sel_row["Product"], sel_row["Qty"],
                                               sel_row["Price"], "rejected", reason=reason)
                        except Exception:
                            pass
                    _set_status(sel_id, "rejected")
                    _invalidate_admin_cache()
                    st.markdown('<div class="success-box">✓ Rejected.</div>',
                                unsafe_allow_html=True)
                    st.rerun()

            st.markdown("---")
            st.markdown("### 🗑 Delete Offer")
            del_id = st.number_input("Offer ID", min_value=1, step=1, key="del_off")
            if st.button("Delete", key="del_off_btn"):
                _delete_offer(int(del_id))
                st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Vendors & Blacklist
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### All Vendors")
        df_v = _cached_vendors()
        if not df_v.empty:
            st.dataframe(df_v, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🚫 Vendor Blacklist")
        st.markdown('<div class="info-box">Blacklisted emails cannot submit offers via the website.</div>',
                    unsafe_allow_html=True)

        bl = _cached_blacklist()
        if bl:
            bl_df = pd.DataFrame(bl, columns=["Email","Reason","Added At"])
            st.dataframe(bl_df, use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="info-box">No blacklisted vendors.</div>',
                        unsafe_allow_html=True)

        st.markdown('<div class="section-label">Add to blacklist</div>', unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1: bl_email  = st.text_input("Email address", key="bl_email")
        with bc2: bl_reason = st.text_input("Reason (optional)", key="bl_reason")
        if st.button("🚫 Blacklist", key="bl_add"):
            if bl_email.strip():
                add_to_blacklist(bl_email.strip(), bl_reason.strip())
                st.markdown(f'<div class="success-box">✓ {bl_email} blacklisted.</div>',
                            unsafe_allow_html=True)
                st.rerun()

        st.markdown('<div class="section-label">Remove from blacklist</div>', unsafe_allow_html=True)
        rm_email = st.text_input("Email to remove", key="bl_rm")
        if st.button("✅ Remove", key="bl_rm_btn"):
            remove_from_blacklist(rm_email.strip())
            _invalidate_admin_cache()
            st.markdown(f'<div class="success-box">✓ {rm_email} removed.</div>',
                        unsafe_allow_html=True)
            st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Analytics + Price History Graph
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        from frontend.analytics import render as render_analytics
        render_analytics()

        # ── Price History per Product ─────────────────────────────────────────
        st.markdown("---")
        st.markdown("## 📈 Accepted Price History")
        st.markdown('<div class="info-box">Average accepted price per product tracked weekly. Shows procurement price trends over time.</div>',
                    unsafe_allow_html=True)

        ph_df = _cached_price_history()

        if ph_df.empty:
            st.markdown('<div class="info-box">No accepted offers yet to show price history.</div>',
                        unsafe_allow_html=True)
        else:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            BG      = "#0d0f14"
            CARD_BG = "#161a24"
            BORDER  = "#2a2f3e"
            MUTED   = "#6b7280"
            COLORS  = ["#e8d5a3","#7c9cbf","#7fbf7c","#bf7c7c","#bf9d7c","#a07cbf"]

            products = ph_df["Product"].unique()

            # Product selector
            sel_ph = st.multiselect(
                "Select products to display",
                options=[p.title() for p in products],
                default=[p.title() for p in products[:3]],
                key="ph_sel"
            )

            fig, ax = plt.subplots(figsize=(10, 4))
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(CARD_BG)
            ax.tick_params(colors=MUTED, labelsize=9)
            ax.set_ylabel("Avg Accepted Price (₹/kg)", color=MUTED, fontsize=9)
            ax.grid(axis="y", color=BORDER, linewidth=0.5, linestyle="--")
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)

            plotted = 0
            for i, product in enumerate(products):
                if product.title() not in sel_ph:
                    continue
                subset = ph_df[ph_df["Product"] == product]
                weekly = subset.groupby("Week")["Price"].mean()
                if len(weekly) >= 1:
                    ax.plot(weekly.index, weekly.values,
                            marker="o", linewidth=2.5, markersize=5,
                            color=COLORS[i % len(COLORS)], label=product.title())
                    # Annotate last point
                    ax.annotate(
                        f"₹{weekly.values[-1]:.0f}",
                        xy=(weekly.index[-1], weekly.values[-1]),
                        xytext=(6, 4), textcoords="offset points",
                        color=COLORS[i % len(COLORS)], fontsize=8
                    )
                    plotted += 1

            if plotted:
                ax.legend(facecolor=CARD_BG, edgecolor=BORDER,
                          labelcolor=MUTED, fontsize=8)
                plt.xticks(rotation=30, ha="right", fontsize=8, color=MUTED)
                plt.tight_layout()
                st.pyplot(fig)
                plt.close()

                # Summary table
                st.markdown('<div class="section-label">Price summary (accepted offers only)</div>',
                            unsafe_allow_html=True)
                summary = ph_df.groupby("Product")["Price"].agg(
                    ["mean","min","max","count"]
                ).round(1).reset_index()
                summary.columns = ["Product","Avg (₹/kg)","Min (₹/kg)","Max (₹/kg)","Count"]
                summary["Product"] = summary["Product"].str.title()
                st.dataframe(summary, use_container_width=True, hide_index=True)
            else:
                plt.close()
                st.markdown('<div class="info-box">Select at least one product above.</div>',
                            unsafe_allow_html=True)

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
                        sender_email = m.extract_email_address(sender)
                        if m.is_automated_email(sender) or m.is_admin_email(sender):
                            skipped += 1
                        elif is_blacklisted(sender_email):
                            skipped += 1
                        else:
                            email["sender_email"] = sender_email
                            valid_emails.append(email)

                    st.info(f"Fetched {len(all_emails)} — {len(valid_emails)} valid, {skipped} skipped.")

                    if valid_emails:
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
                                        send_stock_exceeded_reply(ve, offer.get("vendor",""), prod, qty, avail)
                                continue
                            try:
                                save_offer(offer)
                                saved += 1
                            except Exception:
                                skipped += 1

                        # Check low stock after pipeline
                        new_alerts = check_low_stock_alerts()
                        if new_alerts:
                            send_low_stock_alert(ADMIN_EMAIL, new_alerts)

                        st.markdown(
                            f'<div class="success-box">✓ Done — <b>{saved}</b> saved · '
                            f'<b>{exceeded}</b> exceeded stock · <b>{skipped}</b> skipped.'
                            f'{"<br>⚠ Low stock alert sent." if new_alerts else ""}</div>',
                            unsafe_allow_html=True)

                except RuntimeError as e:
                    st.markdown(f'<div class="danger-box">{e}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<div class="danger-box">Pipeline error: {e}</div>',
                                unsafe_allow_html=True)