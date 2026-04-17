import sqlite3

conn = sqlite3.connect("data/vendor_history.db")

print("\n=== VENDORS ===")
for row in conn.execute("SELECT * FROM vendors"):
    print(row)

print("\n=== OFFERS ===")
for row in conn.execute("SELECT * FROM offers"):
    print(row)

print("\n=== PROCESSED EMAILS ===")
for row in conn.execute("SELECT * FROM processed_emails"):
    print(row)

print("\n=== COUNTS ===")
print("Vendors:", conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0])
print("Offers:", conn.execute("SELECT COUNT(*) FROM offers").fetchone()[0])
print("Processed emails:", conn.execute("SELECT COUNT(*) FROM processed_emails").fetchone()[0])

conn.close()