from database.db_manager import get_connection


def get_vendor_orders(vendor):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT total_orders FROM vendors WHERE name=?",
        (vendor,)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return 0


def update_vendor(vendor):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM vendors WHERE name=?", (vendor,))
    row = cursor.fetchone()

    if row:
        cursor.execute(
            "UPDATE vendors SET total_orders = total_orders + 1 WHERE name=?",
            (vendor,)
        )
    else:
        cursor.execute(
            "INSERT INTO vendors (name, total_orders) VALUES (?, 1)",
            (vendor,)
        )

    conn.commit()
    conn.close()