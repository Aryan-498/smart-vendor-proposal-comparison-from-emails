import sqlite3
import os

DATABASE_PATH = "data/vendor_history.db"


def get_connection():
    """Creates a connection to the SQLite database."""

    os.makedirs("data", exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    return conn


def create_tables():
    """Create all required tables if they do not exist."""

    conn = get_connection()
    cursor = conn.cursor()

    # Vendor table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vendors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        total_orders INTEGER DEFAULT 0,
        last_seen TEXT
    )
    """)

    # Offers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product TEXT,
        quantity REAL,
        unit TEXT,
        price REAL,
        vendor TEXT,
        intent TEXT,
        email_date TEXT
    )
    """)

    # IMPROVEMENT: track processed email IDs to prevent duplicate inserts
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT UNIQUE,
        processed_at TEXT DEFAULT (datetime('now'))
    )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")