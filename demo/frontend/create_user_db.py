import sqlite3

conn = sqlite3.connect("UserDb.sqlite3")
conn.row_factory = sqlite3.Row

cur = conn.cursor()
cur.execute("CREATE TABLE userdb(id integer, name varchar, password varchar, prefs_json varchar) ") 

import random
import simplejson as json
data = json.loads(open("USER_DB", "r").read())
for user in data["users"]:
    password = str(random.randint(10000,99999))
    cur.execute("INSERT INTO userdb (id,name,password,prefs_json) VALUES (?, ?, ?, ?);",
           [user["id"], user["name"], password, json.dumps(user["prefs"])]
    )    
conn.commit()
conn.close()
