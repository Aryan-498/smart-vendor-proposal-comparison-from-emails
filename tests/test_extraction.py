import sys
import os
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

conn = sqlite3.connect("data/vendor_history.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM offers")

rows = cursor.fetchall()

print("Stored offers:")

for row in rows:
    print(row)