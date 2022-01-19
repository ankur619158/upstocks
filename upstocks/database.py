import sqlite3 as sql

con = sql.connect(r'C:\Users\Home\sqlite\test.db')
cur = con.cursor()
value = cur.execute("SELECT * FROM USER;")
print(value)
