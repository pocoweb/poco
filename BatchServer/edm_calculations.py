import datetime
from common.utils import getSiteDBCollection
from common.utils import getLatestUserOrderDatetime


def insertUserOrderFromRawLog(connection, site_id, raw_log):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    amount = 0
    for order_item in raw_log["order_content"]:
        amount += float(order_item["price"]) * int(order_item["amount"])
    c_user_orders.insert({"user_id": raw_log["filled_user_id"], "order_datetime": raw_log["created_on"],
                          "raw_log_id": raw_log["_id"], "amount": amount})


def doUpdateUserOrdersCollection(connection, site_id):
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    latest_order_datetime = getLatestUserOrderDatetime(connection, site_id)
    query_condition = {"behavior": "PLO"}
    if latest_order_datetime is not None:
        query_condition["created_on"] = {"$gt": latest_order_datetime}
    # scan for and add new user_orders
    # NOTE: sort "created_on" to ensure scanning from oldest to newest (otherwise we will miss some logs next time if this process fails on the half way)
    for raw_log in c_raw_logs.find(query_condition).sort("created_on", 1):
        if raw_log.has_key("filled_user_id") and not raw_log["filled_user_id"].startswith("ANO_"):
            insertUserOrderFromRawLog(connection, site_id, raw_log)
    # process those raw_logs which was previously filled with an "ANO_" user id and now got identified as a registered user.
    c_tmp_user_identified_logs_plo = getSiteDBCollection(connection, site_id, "tmp_user_identified_logs_plo")
    for tmp_user_identified_log_plo in c_tmp_user_identified_logs_plo.find():
        raw_log = c_raw_logs.find_one({"_id": tmp_user_identified_log_plo["log_id"]})
        insertUserOrderFromRawLog(connection, site_id, raw_log)
        c_tmp_user_identified_logs_plo.remove({"_id": tmp_user_identified_log_plo["_id"]})

