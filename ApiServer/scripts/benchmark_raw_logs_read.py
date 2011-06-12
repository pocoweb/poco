import sys
sys.path.insert(0, "../../")
import pymongo
from common.utils import getSiteDBCollection, getSiteDB
import time


connection = pymongo.Connection()
coll = getSiteDBCollection(connection, "demo1", "raw_logs")
t0 = time.time()
#for row in coll.find().sort("$natural", -1):
#    pass
for row in coll.find().sort("timestamp", -1):
    pass
print time.time() - t0
