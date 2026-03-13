import sqlite3

DB_PATH = "data/vendor_history.db"


def reset_database():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM offers")
    cursor.execute("DELETE FROM vendors")

    # reset auto increment counters
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='offers'")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='vendors'")

    conn.commit()
    conn.close()

    print("Database reset successful.")


if __name__ == "__main__":
    reset_database()