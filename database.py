import sqlite3

conn = sqlite3.connect("orders.db")

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    food TEXT,
    quantity INTEGER,
    address TEXT,
    message TEXT
)
""")

conn.commit()
conn.close()

print("Database Created Successfully!")