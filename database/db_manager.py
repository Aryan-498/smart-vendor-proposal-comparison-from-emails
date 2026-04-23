import sqlite3
import os

DATABASE_PATH = "data/vendor_history.db"


def get_connection():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        total_orders INTEGER DEFAULT 0,
        last_seen TEXT
    )""")

    # Added: source column ('email' or 'web'), user_email for web offers
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        quantity REAL,
        unit TEXT,
        price REAL,
        vendor TEXT,
        intent TEXT,
        email_date TEXT,
        source TEXT DEFAULT 'email',
        user_email TEXT DEFAULT NULL,
        vendor_email TEXT DEFAULT NULL,
        status TEXT DEFAULT 'pending'
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT UNIQUE,
        processed_at TEXT DEFAULT (datetime('now'))
    )""")

    # Add missing columns to existing DBs gracefully
    for col, definition in [
        ("source",       "TEXT DEFAULT 'email'"),
        ("user_email",   "TEXT DEFAULT NULL"),
        ("vendor_email", "TEXT DEFAULT NULL"),
        ("status",       "TEXT DEFAULT 'pending'"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE offers ADD COLUMN {col} {definition}")
        except Exception:
            pass  # column already exists

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")

# Run this to add contact columns to existing DB
def add_contact_columns():
    conn = get_connection()
    cursor = conn.cursor()
    for col, defn in [
        ("phone",         "TEXT DEFAULT NULL"),
        ("address",       "TEXT DEFAULT NULL"),
        ("note",          "TEXT DEFAULT NULL"),
        ("counter_price", "REAL DEFAULT NULL"),
        ("user_response", "TEXT DEFAULT NULL"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE offers ADD COLUMN {col} {defn}")
        except Exception:
            pass
    conn.commit()
    conn.close()