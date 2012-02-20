import sys; sys.path.insert(0, "../")
import datetime
from common.utils import getSiteDBCollection


def insertUserOrderFromRawLog(connection, site_id, raw_log):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    amount = 0
    for order_item in raw_log["order_content"]:
        amount += float(order_item["price"]) * int(order_item["amount"])
    c_user_orders.insert({"user_id": raw_log["filled_user_id"], "order_datetime": raw_log["created_on"],
                          "raw_log_id": raw_log["_id"], "amount": amount})

def getLatestOrderDatetime(connection, site_id):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    last_user_orders = [user_order for user_order in c_user_orders.find().sort("order_datetime", -1).limit(1)]
    if len(last_user_orders) == 0:
        latest_order_datetime = None
    else:
        latest_order_datetime = last_user_orders[0]["order_datetime"]
    return latest_order_datetime

def doUpdateUserOrdersCollection(connection, site_id):
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    latest_order_datetime = getLatestOrderDatetime(connection, site_id)
    query_condition = {"behavior": "PLO"}
    if latest_order_datetime is not None:
        query_condition["created_on"] = {"$gt": latest_order_datetime}
    # scan for and add new user_orders
    for raw_log in c_raw_logs.find(query_condition):
        if raw_log.has_key("filled_user_id") and not raw_log["filled_user_id"].startswith("ANO_"):
            insertUserOrderFromRawLog(connection, site_id, raw_log)
    # process those raw_logs which was previously filled with an "ANO_" user id and now got identified as a registered user.
    c_tmp_user_identified_logs_plo = getSiteDBCollection(connection, site_id, "tmp_user_identified_logs_plo")
    for tmp_user_identified_log_plo in c_tmp_user_identified_logs_plo.find():
        raw_log = c_raw_logs.find_one({"_id": tmp_user_identified_log_plo["log_id"]})
        insertUserOrderFromRawLog(connection, site_id, raw_log)
        c_tmp_user_identified_logs_plo.remove({"_id": tmp_user_identified_log_plo["_id"]})


def getUsersForEmailing(connection, site_id):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    latest_order_datetime = getLatestOrderDatetime(connection, site_id)
    order_datetime_7days_ago = latest_order_datetime - datetime.timedelta(days=7)
    user_ids_map = {}
    for user_order in c_user_orders.find({"order_datetime": {"$gte": order_datetime_7days_ago, "$lte": latest_order_datetime}}):
        user_ids_map[user_order["user_id"]] = 1
    return user_ids_map.keys()


def getViewedUltimatelyBought(user_id):
    pass


def _backfill(connection):
    from preprocessing import backfiller
    bFiller = backfiller.BackFiller(connection, "kuaishubao", None, settings.work_dir + "/backfilled_raw_logs")
    bFiller.start()


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    import pymongo
    import settings
    connection = pymongo.Connection(settings.mongodb_host)

    #_backfill(connection)
    #doUpdateUserOrdersCollection(connection, "kuaishubao")
    print getUsersForEmailing(connection, "kuaishubao")
