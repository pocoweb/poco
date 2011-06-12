import sys
sys.path.insert(0, "../")
import time
from common.utils import getSiteDBCollection
import pymongo


connection = pymongo.Connection()
item_similarities = getSiteDBCollection(connection, "demo2", "raw_logs")
t1 = time.time()
for i in xrange(10000):
    item_similarities.find_one()
t2 = time.time()
print t2 - t1

t1 = time.time()
count = 0
for row in item_similarities.find().sort("timestamp", -1):
    count += 1
    if count > 10000: break
t2 = time.time()
print t2 - t1
