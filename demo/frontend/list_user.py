import sqlite3
import random


conn = sqlite3.connect("UserDb.sqlite3")
conn.row_factory = sqlite3.Row

cur = conn.cursor()
cur.execute("SELECT id, name, password, prefs_json FROM userdb;")
for id, name, password, prefs_json in cur.fetchall():
    print name, password
conn.close()
