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


def getUsersForEmailing(connection, site_id):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    latest_order_datetime = getLatestOrderDatetime(connection, site_id)
    order_datetime_7days_ago = latest_order_datetime - datetime.timedelta(days=14)
    user_ids_map = {}
    for user_order in c_user_orders.find({"order_datetime": {"$gte": order_datetime_7days_ago, "$lte": latest_order_datetime}}):
        user_ids_map[user_order["user_id"]] = 1
    return user_ids_map.keys()


def getUserViewedItemList(user_id, max_items):
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    [raw_log["item_id"] for raw_log in c_raw_logs.find({"filled_user_id": user_id, "behavior": "V"}).sort({"created_on": -1}).limit(max_items)]


from ApiServer.mongo_client import MongoClient
from ApiServer.mongo_client import SimpleRecommendationResultFilter

def recommendForUser(connection, site_id, user_id, max_amount=5):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    latest_user_order = [user_order for user_order in c_user_orders.find({"user_id": user_id}).sort("order_datetime", -1).limit(1)][0]
    raw_log = c_raw_logs.find_one({"_id": latest_user_order["raw_log_id"]})
    items_list = [order_item["item_id"] for order_item in raw_log["order_content"]]
    mongo_client = MongoClient(connection)
    purchasing_history = mongo_client.getPurchasingHistory(site_id, user_id)["purchasing_history"]
    topn = mongo_client.calc_weighted_top_list_method1(site_id, "PLO", items_list, extra_excludes_list=purchasing_history)
    return mongo_client.convertTopNFormat(site_id, req_id=None, result_filter=SimpleRecommendationResultFilter(),
                    topn=topn, amount=max_amount, include_item_info=True, deduplicate_item_names_required=True,
                    url_converter=lambda item_link, site_id, item_id, req_id: item_link)


def _backfill(connection):
    from preprocessing import backfiller
    bFiller = backfiller.BackFiller(connection, "kuaishubao", None, settings.work_dir + "/backfilled_raw_logs")
    bFiller.start()


def test(connection):
    user_ids = getUsersForEmailing(connection, "kuaishubao")
    for user_id in user_ids[:5]:
        print user_id
        result, _ = recommendForUser(connection, "kuaishubao", user_id)
        for recommended_item in result:
        #    print recommended_item
            print recommended_item["item_name"], recommended_item["item_link"]
        print "====================================="


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    import pymongo
    import settings
    connection = pymongo.Connection(settings.mongodb_host)

    #_backfill(connection)
    #doUpdateUserOrdersCollection(connection, "kuaishubao")

    #test(connection)
