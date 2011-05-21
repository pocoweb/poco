import os
import time
import hashlib
import hbase_client


os.system("python init_database.py test1 deleteOld")

session_id1 = "s00127"
session_id2 = "s00128"

hbase_client.insertBrowsingHistory("test1", session_id1, "5511", 1000010.0)
hbase_client.insertBrowsingHistory("test1", session_id2, "5511", 1000011.0)
hbase_client.insertBrowsingHistory("test1", session_id1, "5512", 1000020.0)
hbase_client.insertBrowsingHistory("test1", session_id2, "5599", 1000023.0)
hbase_client.insertBrowsingHistory("test1", session_id1, "5535", 1000025.0)

t0 = time.time()
hbase_client.fetchRecentNBrowsingHistory("test1", session_id1, n=10)
t1 = time.time()
hbase_client.fetchRecentNBrowsingHistory("test1", session_id2, n=10)
t2 = time.time()
print t1 - t0, t2 - t1
