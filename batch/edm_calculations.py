import datetime
import time
import logging
from common.utils import getSiteDBCollection
from common.utils import getSiteDB
from common.utils import getLatestUserOrderDatetime
from api.mongo_client import MongoClient


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


# NOTE: This function is only for small set of data
EMAILING_USER_ORDERS_MAX_DAY = 14
EXPECTED_RECOMMENDATION_ITEMS = 5
def generateEdmEmailingList(connection, site_id):
    logger = logging.getLogger("EDMCalculations")
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    latest_order_datetime = getLatestUserOrderDatetime(connection, site_id)
    if latest_order_datetime is None:
        query = {}
    else:
        query = {"order_datetime": {"$gte": latest_order_datetime \
                                - datetime.timedelta(days=EMAILING_USER_ORDERS_MAX_DAY)}}
    db = getSiteDB(connection, site_id)
    result = db.command({"distinct": "user_orders", "key": "user_id", 
                "query": query})
    user_ids = result["values"]
    
    mongo_client = MongoClient(connection)
    c_edm_emailing_list = getSiteDBCollection(connection, site_id, "edm_emailing_list")
    c_edm_emailing_list.drop()
    c_edm_emailing_list = getSiteDBCollection(connection, site_id, "edm_emailing_list")
    count = 0
    t0 = time.time()
    for user_id in user_ids:
        count += 1
        if count % 100 == 0:
            logger.info("Count: %s, %s users/sec" % (count, count/(time.time() - t0)))
        recommendation_result, _ = mongo_client.recommend_for_edm(site_id, user_id, 
                                        max_amount=EXPECTED_RECOMMENDATION_ITEMS)
        if len(recommendation_result) == EXPECTED_RECOMMENDATION_ITEMS:
            c_edm_emailing_list.insert({"user_id": user_id, "recommendation_result": recommendation_result})
