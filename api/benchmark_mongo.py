#!/usr/bin/env python

import sys
sys.path.insert(0, "../")
import time
import pymongo
import settings


connection = pymongo.Connection(settings.mongodb_host)
connection.drop_database("benchmarkdb1")
connection["benchmarkdb1"].create_collection("coll", {"capped":True, "size": 102400000})
collection = connection["benchmarkdb1"]["coll"]
#collection.ensure_index([("number", pymongo.DESCENDING)])


t1 = time.time()
count = 50000
for number in range(count):
    collection.insert({"number": number, "name": "NAME:%s" % number})
t2 = time.time()
print "Insert %d %s" % (count, t2 - t1)


t1 = time.time()
count = 0
for row in collection.find().sort("$natural", -1):
    count += 1
    if count > 5000: break
t2 = time.time()
print "find 5000 docs %s" % (t2 - t1)
