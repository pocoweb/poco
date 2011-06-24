import sys
sys.path.insert(0, "../")
import pymongo
from common.utils import getSiteDBCollection
import settings


connection = pymongo.Connection(settings.mongodb_host)
for site in connection["tjb-db"]["sites"].find():
    site_id = site["site_id"]
    print "Work on %s" % site_id
    raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    for row in raw_logs.find():
        if isinstance(row["timestamp"], basestring) and row["timestamp"].endswith("+0"):
            raw_logs.update(row, 
                {"$set": {"timestamp": float(row["timestamp"][:-2])}})
        if row.has_key("tuijianbaoid"):
            raw_logs.update(row,
                {"$set": {"tjbid": row["tuijianbaoid"]}})
