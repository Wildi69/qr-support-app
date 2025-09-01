import sqlite3

con = sqlite3.connect("dev.db")
cur = con.cursor()

rows = cur.execute("SELECT id, operator_name, operator_phone, summary, status, created_at FROM tickets").fetchall()
for row in rows:
    print(row)

con.close()
