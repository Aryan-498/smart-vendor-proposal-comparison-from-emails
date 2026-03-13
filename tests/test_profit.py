import sqlite3

conn = sqlite3.connect("data/vendor_history.db")
cursor = conn.cursor()

cursor.execute("SELECT product, quantity, price, vendor, intent FROM offers")

rows = cursor.fetchall()

print("\nStored Offers:\n")

for row in rows:
    print(row)

conn.close()