from database.db_manager import get_connection
from utils.logger import log


def save_offer(offer):
    """Saves an extracted offer into the database."""

    conn = get_connection()
    cursor = conn.cursor()

    product = offer.get("product")
    quantity = offer.get("quantity")
    unit = offer.get("unit")
    price = offer.get("price")
    vendor = offer.get("vendor")
    intent = offer.get("intent")

    # IMPROVEMENT: validate required fields before writing
    if not product or price is None:
        log(f"Skipping offer with missing product or price: {offer}")
        conn.close()
        return

    cursor.execute("""
        INSERT INTO offers (product, quantity, unit, price, vendor, intent, email_date)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (product, quantity, unit, price, vendor, intent))

    # Upsert vendor record
    cursor.execute("SELECT id FROM vendors WHERE name = ?", (vendor,))
    vendor_row = cursor.fetchone()

    if vendor_row is None:
        cursor.execute("""
            INSERT INTO vendors (name, total_orders, last_seen)
            VALUES (?, 1, datetime('now'))
        """, (vendor,))
    else:
        cursor.execute("""
            UPDATE vendors
            SET total_orders = total_orders + 1,
                last_seen = datetime('now')
            WHERE name = ?
        """, (vendor,))

    conn.commit()
    conn.close()