import sys
sys.path.insert(0, "../")
import time
from common.utils import getSiteDBCollection
import pymongo


connection = pymongo.Connection()
item_similarities = getSiteDBCollection(connection, "demo1", "item_similarities")
t1 = time.time()
for i in xrange(10000):
    item_similarities.find_one({"item_id": "880001"})
t2 = time.time()
print t2 - t1
