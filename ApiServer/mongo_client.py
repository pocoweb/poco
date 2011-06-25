import pymongo
import hashlib
import urllib
import random
import time

from common.utils import getSiteDBName
from common.utils import getSiteDBCollection
from common.utils import sign

import settings


connection = pymongo.Connection(settings.mongodb_host)


cache = {}
def getCachedVAV(site_id, history_item):
    global cache
    if not cache.has_key((site_id, history_item)):
        cache[(site_id, history_item)] = recommend_viewed_also_view(site_id, str(history_item), 15)
    return cache[(site_id, history_item)]


def recommend_viewed_also_view(site_id, similarity_type, item_id, amount):
    item_similarities = getSiteDBCollection(connection, site_id, "item_similarities_%s" % similarity_type)
    result = item_similarities.find_one({"item_id": item_id})
    if result is not None:
        most_similar_items = result["mostSimilarItems"]
    else:
        most_similar_items = []
    if len(most_similar_items) > amount:
        topn = most_similar_items[:amount]
    else:
        topn = most_similar_items
    return topn


MAX_PURCHASING_HISTORY_AMOUNT = 100
# ASSUME use will not purchase so quickly that the order of two purchasing will be reversed.
# ASSUMING purchasing speed is far slower than page view.
# there is a small chance that the "purchasing_history" will not 100% correctly reflect the raw_log
def updateUserPurchasingHistory(site_id, user_id):
    c_purchasing_history = getSiteDBCollection(connection, site_id, "purchasing_history")
    ph_in_db = c_purchasing_history.find_one({"user_id": user_id})
    if ph_in_db is None:
        ph_in_db = {"user_id": user_id, "purchasing_history": []}
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    cursor = c_raw_logs.find({"user_id": user_id, "behavior": "PLO"}).sort("timestamp", -1).limit(MAX_PURCHASING_HISTORY_AMOUNT)
    is_items_enough = False
    purchasing_history = []
    ph_map = {}
    for record_PLO in cursor:
        for order_item in record_PLO["order_content"]:
            item_id = order_item["item_id"]
            if not ph_map.has_key(item_id):
                purchasing_history.append(item_id)
                ph_map[item_id] = 1
            if len(purchasing_history) > MAX_PURCHASING_HISTORY_AMOUNT:
                is_items_enough = True
                break
        if is_items_enough:
            break
    ph_in_db["purchasing_history"] = purchasing_history
    c_purchasing_history.save(ph_in_db)


def get_purchasing_history(site_id, user_id):
    c_purchasing_history = getSiteDBCollection(connection, site_id, "purchasing_history")
    ph_in_db = c_purchasing_history.find_one({"user_id": user_id})
    if ph_in_db is None:
        ph_in_db = {"user_id": user_id, "purchasing_history": []}
    return ph_in_db


def recommend_based_on_purchasing_history(site_id, user_id, amount):
    purchasing_history = get_purchasing_history(site_id, user_id)["purchasing_history"]
    if len(purchasing_history) > 15:
        purchasing_history = purchasing_history[:15]
    topn = calc_weighted_top_list_method1(site_id, similarity_type, purchasing_history) 
    if len(topn) > amount:
        topn = topn[:amount]
    return topn


def recommend_viewed_ultimately_buy(site_id, item_id, amount):
    viewed_ultimately_buys = getSiteDBCollection(connection, site_id, "viewed_ultimately_buys")
    result = viewed_ultimately_buys.find_one({"item_id": item_id})
    if result is not None:
        vubs = result["viewedUltimatelyBuys"]
    else:
        vubs = []
    if len(vubs) > amount:
        topn = vubs[:amount]
    else:
        topn = vubs
    return [(topn_item["item_id"], topn_item["percentage"]) for topn_item in topn]


def getSimilaritiesForItems(site_id, similarity_type, item_ids):
    item_similarities = getSiteDBCollection(connection, site_id, "item_similarities_%s" % similarity_type)
    result = []
    for row in item_similarities.find({"item_id": {"$in": item_ids}}):
        most_similar_items = row["mostSimilarItems"]
        result.append(most_similar_items)
    return result


sites = connection["tjb-db"]["sites"]

API_KEY2SITE_ID = None
SITE_ID2API_KEY = None

def reloadApiKey2SiteID():
    global API_KEY2SITE_ID
    global SITE_ID2API_KEY
    API_KEY2SITE_ID = {}
    SITE_ID2API_KEY = {}
    for site in sites.find():
        API_KEY2SITE_ID[site["api_key"]] = site["site_id"]
        SITE_ID2API_KEY[site["site_id"]] = site["api_key"]


def getApiKey2SiteID():
    global API_KEY2SITE_ID
    if API_KEY2SITE_ID is None:
        reloadApiKey2SiteID()
    return API_KEY2SITE_ID


def loadSites():
    return [site for site in sites.find()]


# FIXME; should also make the api_key field unique.
def generateApiKey(site_id, site_name):
    api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
    while sites.find_one({"api_key": api_key}) is not None:
        api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
    return api_key

class UpdateSiteError(Exception):
    pass

def updateSite(site_id, site_name, calc_interval):
    site = sites.find_one({"site_id": site_id})
    if site is None:
        if site_name is None:
            raise UpdateSiteError("site_name is required for new site creation.")
        site = {"site_id": site_id}
    site.setdefault("last_update_ts", None)
    site.setdefault("disabledFlows", [])
    site.setdefault("api_key", generateApiKey())
    if site_name is not None:
        site["site_name"] = site_name
    site["calc_interval"] = calc_interval
    sites.save(site)


def updateItem(site_id, item):
    items = getSiteDBCollection(connection, site_id, "items")
    item_in_db = items.find_one({"item_id": item["item_id"]})
    if item_in_db is None:
        item_in_db = {}
    else:
        item_in_db = {"_id": item_in_db["_id"]}
    item_in_db.update(item)
    item_in_db["available"] = True
    items.save(item_in_db)


def removeItem(site_id, item_id):
    items = getSiteDBCollection(connection, site_id, "items")
    item_in_db = items.find_one({"item_id": item_id})
    if item_in_db is not None:
        item_in_db["available"] = False
        items.save(item_in_db)


def getItem(site_id, item_id):
    items = getSiteDBCollection(connection, site_id, "items")
    return items.find_one({"item_id": item_id})


def getRedirectUrlFor(url, site_id, item_id, req_id):
    api_key = SITE_ID2API_KEY[site_id]
    param_str = urllib.urlencode({"url": url, "api_key": api_key, "item_id": item_id,
                      "req_id": req_id})
    full_url = settings.api_server_prefix + "/1.0/redirect?" + param_str
    return full_url


def convertTopNFormat(site_id, req_id, topn, include_item_info=True):
    items_collection = getSiteDBCollection(connection, site_id, "items")
    result = []
    for topn_row in topn:
        if include_item_info:
            item_in_db = items_collection.find_one({"item_id": topn_row[0]})
            if item_in_db is None or item_in_db["available"] == False:
                continue
            del item_in_db["_id"]
            del item_in_db["available"]
            item_in_db["score"] = topn_row[1]
            item_in_db["item_link"] = getRedirectUrlFor(item_in_db["item_link"], site_id, 
                                            item_in_db["item_id"], req_id)
            result.append(item_in_db)
        else:
            result.append({"item_id": topn_row[0], "score": topn_row[1]})
    return result


def calc_weighted_top_list_method1(site_id, similarity_type, browsing_history):
    if len(browsing_history) > 15:
        recent_history = browsing_history[:15]
    else:
        recent_history = browsing_history

    # calculate weighted top list from recent browsing history
    rec_map = {}
    for recommended_items in getSimilaritiesForItems(site_id, similarity_type, recent_history):
        for rec_item, score in recommended_items:
            if rec_item not in browsing_history:
                rec_map.setdefault(rec_item, [0,0])
                rec_map[rec_item][0] += float(score)
                rec_map[rec_item][1] += 1
    rec_tuples = []
    for key in rec_map.keys():
        score_total, count = rec_map[key][0], rec_map[key][1]
        rec_tuples.append((key, score_total / count))
    rec_tuples.sort(lambda a,b: sign(b[1] - a[1]))
    return [rec_tuple for rec_tuple in rec_tuples]


def recommend_based_on_browsing_history(site_id, similarity_type, browsing_history, amount):
    topn = calc_weighted_top_list_method1(site_id, similarity_type, browsing_history) 
    if len(topn) > amount:
        topn = topn[:amount]
    return topn


# Logging Part
def writeLogToMongo(site_id, content):
    raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    raw_logs.ensure_index([("timestamp", pymongo.DESCENDING)])
    raw_logs.insert(content)

