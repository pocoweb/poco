import sys
sys.path.insert(0, "../")
import time
import pymongo


connection = pymongo.Connection()
collection = connection["benchmarkdb1"]["coll"]
collection.ensure_index([("number", pymongo.DESCENDING)])

t1 = time.time()
for number in range(50000):
    collection.insert({"number": number, "name": "NAME:%s" % number})
t2 = time.time()
print t2 - t1
