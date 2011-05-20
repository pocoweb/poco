import sqlite3
import random

conn = sqlite3.connect("UserDb.sqlite3")
conn.row_factory = sqlite3.Row

name = raw_input("name:")
password = str(random.randint(10000, 99999))
print "password is:", password

cur = conn.cursor()
cur.execute("SELECT max(id) FROM userdb;")
max_id = cur.fetchone()[0]
cur.execute("INSERT INTO userdb (id, name, password, prefs_json) VALUES (?, ?, ?, ?)", (max_id + 1, name, password, "[]"))
conn.commit()
conn.close()
