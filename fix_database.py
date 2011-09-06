import sys
import datetime
import uuid
import pymongo
from common.utils import getSiteDBCollection
from common.utils import smart_split


if len(sys.argv) != 2:
    print "Usage: fix_database.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]


connection = pymongo.Connection(mongodb_host)


if False:
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
            if not row.has_key("order_id"):
                raw_logs.update(row,
                    {"$set": {"order_id": None}})
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
        if not site.has_key("algorithm_type"):
            sites.update({"site_id": site["site_id"]},
                        {"$set": {"algorithm_type": "llh"}})
    print "=======================\n"


if False:
    print "Fix Users"
    c_users = connection["tjb-db"]["users"]
    for user in c_users.find():
        if not user.has_key("is_admin"):
            c_users.update({"user_name": user["user_name"]},
                           {"$set": {"is_admin": False}})

    print "Fix PLO order_content"
    sites = connection["tjb-db"]["sites"]
    for site in sites.find():
        print "Work on:", site["site_name"]
        c_raw_logs = getSiteDBCollection(connection, site["site_id"], "raw_logs")
        for raw_log in c_raw_logs.find({"behavior": "PLO"}):
            order_content = raw_log["order_content"]
            for order_item in order_content:
                order_item["price"] = order_item["price"].strip()
            c_raw_logs.save(raw_log)
            #c_raw_logs.update(raw_log, {"$set": {"order_content": order_content}})


    print "Fix recommended_items "
    sites = connection["tjb-db"]["sites"]
    for site in sites.find():
        print "Work on:", site["site_name"]
        c_raw_logs = getSiteDBCollection(connection, site["site_id"], "raw_logs")
        for raw_log in c_raw_logs.find():
            if raw_log["behavior"].startswith("Rec"):
                if not raw_log.has_key("recommended_items"):
                    raw_log["recommended_items"] = []
                    c_raw_logs.save(raw_log)


    print "set is_empty_result "
    sites = connection["tjb-db"]["sites"]
    for site in sites.find():
        print "Work on:", site["site_name"]
        c_raw_logs = getSiteDBCollection(connection, site["site_id"], "raw_logs")
        for raw_log in c_raw_logs.find({"recommended_items": {"$exists": True}, "is_empty_result": {"$exists": False}}):
            #print raw_log
            if raw_log["behavior"].startswith("Rec") and not raw_log.has_key("is_empty_result"):
                raw_log["is_empty_result"] = len(raw_log["recommended_items"]) == 0
                c_raw_logs.save(raw_log)


print "Convert Timestamp from float to datetime and add uniq_order_id"
sites = connection["tjb-db"]["sites"]
for site in sites.find():
    print "Work on:", site["site_name"]
    c_raw_logs = getSiteDBCollection(connection, site["site_id"], "raw_logs")
    for raw_log in c_raw_logs.find():
        if raw_log.has_key("timestamp"):
            if isinstance(raw_log["timestamp"], float):
                raw_log["timestamp"] = datetime.datetime.fromtimestamp(raw_log["timestamp"])
            raw_log["created_on"] = raw_log["timestamp"]
            del raw_log["timestamp"]
        if raw_log["behavior"] == "PLO" and not raw_log.has_key("uniq_order_id"):
            raw_log["uniq_order_id"] = str(uuid.uuid4())
        c_raw_logs.save(raw_log)
    c_raw_logs.ensure_index("created_on", -1, background=True, unique=False)
    c_raw_logs.ensure_index("created_on", 1, background=True, unique=False)
