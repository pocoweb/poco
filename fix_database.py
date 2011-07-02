import sys
import pymongo
from common.utils import getSiteDBCollection
from common.utils import smart_split


if len(sys.argv) != 2:
    print "Usage: fix_database.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]


connection = pymongo.Connection(mongodb_host)


print "Fix Raw Logs"
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
print "=======================\n"


print "Fix Purchasing History"
from ApiServer.mongo_client import MongoClient
mongo_client = MongoClient(connection)
for site in connection["tjb-db"]["sites"].find():
    site_id = site["site_id"]
    print "Work on ", site_id
    raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    user_ids = {}
    for raw_log in raw_logs.find({"behavior": "PLO"}):
        if raw_log["user_id"] != "null":
            user_ids[raw_log["user_id"]] = 1
    print "%s users to update" % len(user_ids)
    for user_id in user_ids.keys():
        mongo_client.updateUserPurchasingHistory(site_id, user_id)
    print "updated for %s" % site_id
print "=======================\n"


print "Fix item categories"
for site in connection["tjb-db"]["sites"].find():
    site_id = site["site_id"]
    print "Work on %s" % site_id
    c_items = getSiteDBCollection(connection, site_id, "items")
    for item_row in c_items.find():
        categories = item_row.get("categories", None)
        if isinstance(categories, basestring):
            c_items.update({"item_id": item_row["item_id"]}, 
                    {"$set": {"categories": smart_split(categories, ",")}})
        elif categories is None:
            c_items.update({"item_id": item_row["item_id"]}, 
                    {"$set": {"categories": []}})
print "=======================\n"


print "Fix sites"
from Adminboard.site_utils import generateApiKey
sites = connection["tjb-db"]["sites"]
for site in sites.find():
    if not site.has_key("api_key"):
        api_key = generateApiKey(connection, site["site_id"], site["site_name"])
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"api_key": api_key}})
    calc_interval = site.get("calc_interval", None)
    if type(calc_interval) != int and calc_interval != None:
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"calc_interval": int(site["calc_interval"])}})
    if not site.has_key("disabledFlows"):
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"disabledFlows": []}})
print "=======================\n"
