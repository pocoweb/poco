import sys
sys.path.insert(0, "../")
import time
import pymongo


connection = pymongo.Connection()
connection.drop_database("benchmarkdb1")
connection["benchmarkdb1"].create_collection("coll", {"capped":True, "size": 102400000})
collection = connection["benchmarkdb1"]["coll"]
#collection.ensure_index([("number", pymongo.DESCENDING)])


t1 = time.time()
for number in range(50000):
    collection.insert({"number": number, "name": "NAME:%s" % number})
t2 = time.time()
print t2 - t1


t1 = time.time()
count = 0
for row in collection.find().sort("$natural", -1):
    count += 1
    if count > 5000: break
t2 = time.time()
print t2 - t1
