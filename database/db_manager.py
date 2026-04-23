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
        last_seen TEXT,
        blacklisted INTEGER DEFAULT 0
    )""")

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
        status TEXT DEFAULT 'pending',
        phone TEXT DEFAULT NULL,
        address TEXT DEFAULT NULL,
        note TEXT DEFAULT NULL,
        counter_price REAL DEFAULT NULL,
        user_response TEXT DEFAULT NULL,
        user_counter_price REAL DEFAULT NULL
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS processed_emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email_id TEXT UNIQUE,
        processed_at TEXT DEFAULT (datetime('now'))
    )""")

    # Vendor blacklist table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blacklist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        reason TEXT,
        added_at TEXT DEFAULT (datetime('now'))
    )""")

    # Migrate existing DBs
    for col, defn in [
        ("source",             "TEXT DEFAULT 'email'"),
        ("user_email",         "TEXT DEFAULT NULL"),
        ("vendor_email",       "TEXT DEFAULT NULL"),
        ("status",             "TEXT DEFAULT 'pending'"),
        ("phone",              "TEXT DEFAULT NULL"),
        ("address",            "TEXT DEFAULT NULL"),
        ("note",               "TEXT DEFAULT NULL"),
        ("counter_price",      "REAL DEFAULT NULL"),
        ("user_response",      "TEXT DEFAULT NULL"),
        ("user_counter_price", "REAL DEFAULT NULL"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE offers ADD COLUMN {col} {defn}")
        except Exception:
            pass

    for col, defn in [("blacklisted", "INTEGER DEFAULT 0")]:
        try:
            cursor.execute(f"ALTER TABLE vendors ADD COLUMN {col} {defn}")
        except Exception:
            pass

    conn.commit()
    conn.close()


def add_contact_columns():
    """Legacy — kept for backward compat. create_tables() now handles all cols."""
    create_tables()


# ── Blacklist helpers ──────────────────────────────────────────────────────────

def is_blacklisted(email: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM blacklist WHERE email=?", (email.lower(),))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_blacklist():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, reason, added_at FROM blacklist ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_to_blacklist(email: str, reason: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO blacklist (email, reason) VALUES (?,?)",
            (email.lower(), reason)
        )
        conn.commit()
    finally:
        conn.close()


def remove_from_blacklist(email: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM blacklist WHERE email=?", (email.lower(),))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully.")