import sys
import pymongo
from common.utils import getSiteDBCollection


if len(sys.argv) != 2:
    print "Usage: fix_database.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]


connection = pymongo.Connection(mongodb_host)


# Fix raw_logs
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


# Fix sites
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