import sqlite3
from database.db_manager import get_connection


def save_offer(offer):
    """
    Saves an extracted offer into the database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    product = offer.get("product")
    quantity = offer.get("quantity")
    unit = offer.get("unit")
    price = offer.get("price")
    vendor = offer.get("vendor")
    intent = offer.get("intent")

    # Insert into offers table
    cursor.execute("""
        INSERT INTO offers (product, quantity, unit, price, vendor, intent, email_date)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
    """, (product, quantity, unit, price, vendor, intent))

    # Check if vendor exists
    cursor.execute("""
        SELECT id FROM vendors WHERE name = ?
    """, (vendor,))

    vendor_row = cursor.fetchone()

    if vendor_row is None:
        # Insert new vendor
        cursor.execute("""
            INSERT INTO vendors (name, total_orders, last_seen)
            VALUES (?, 1, datetime('now'))
        """, (vendor,))
    else:
        # Update existing vendor
        cursor.execute("""
            UPDATE vendors
            SET total_orders = total_orders + 1,
                last_seen = datetime('now')
            WHERE name = ?
        """, (vendor,))

    conn.commit()
    conn.close()