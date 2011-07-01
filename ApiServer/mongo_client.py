import pymongo
import hashlib
import urllib
import random
import time

from common.utils import getSiteDBName
from common.utils import getSiteDBCollection
from common.utils import sign

import settings


class UpdateSiteError(Exception):
    pass


class MongoClient:
    def __init__(self, connection):
        self.connection = connection


    def recommend_viewed_also_view(self, site_id, similarity_type, item_id):
        item_similarities = getSiteDBCollection(self.connection, site_id, 
                "item_similarities_%s" % similarity_type)
        result = item_similarities.find_one({"item_id": item_id})
        if result is not None:
            topn = result["mostSimilarItems"]
        else:
            topn = []
        return topn


    def getPurchasingHistory(self, site_id, user_id):
        c_purchasing_history = getSiteDBCollection(self.connection, site_id, "purchasing_history")
        ph_in_db = c_purchasing_history.find_one({"user_id": user_id})
        if ph_in_db is None:
            ph_in_db = {"user_id": user_id, "purchasing_history": []}
        return ph_in_db


    MAX_PURCHASING_HISTORY_AMOUNT = 100
    # ASSUME use will not purchase so quickly that the order of two purchasing will be reversed.
    # ASSUMING purchasing speed is far slower than page view.
    # there is a small chance that the "purchasing_history" will not 
    # 100% correctly reflect the raw_log
    def updateUserPurchasingHistory(self, site_id, user_id):
        ph_in_db = self.getPurchasingHistory(site_id, user_id)
        c_raw_logs = getSiteDBCollection(self.connection, site_id, "raw_logs")
        cursor = c_raw_logs.find({"user_id": user_id, "behavior": "PLO"}).\
                sort("timestamp", -1).limit(self.MAX_PURCHASING_HISTORY_AMOUNT)
        is_items_enough = False
        purchasing_history = []
        ph_map = {}
        for record_PLO in cursor:
            for order_item in record_PLO["order_content"]:
                item_id = order_item["item_id"]
                if not ph_map.has_key(item_id):
                    purchasing_history.append(item_id)
                    ph_map[item_id] = 1
                if len(purchasing_history) > self.MAX_PURCHASING_HISTORY_AMOUNT:
                    is_items_enough = True
                    break
            if is_items_enough:
                break
        ph_in_db["purchasing_history"] = purchasing_history
        c_purchasing_history = getSiteDBCollection(self.connection, site_id, "purchasing_history")
        c_purchasing_history.save(ph_in_db)


    def recommend_based_on_purchasing_history(self, site_id, user_id):
        purchasing_history = self.getPurchasingHistory(site_id, user_id)["purchasing_history"]
        topn = self.calc_weighted_top_list_method1(site_id, "PLO", purchasing_history) 
        return topn


    def recommend_viewed_ultimately_buy(self, site_id, item_id):
        viewed_ultimately_buys = getSiteDBCollection(self.connection, site_id, "viewed_ultimately_buys")
        result = viewed_ultimately_buys.find_one({"item_id": item_id})
        if result is not None:
            vubs = result["viewedUltimatelyBuys"]
        else:
            vubs = []
        return [(vubs_item["item_id"], vubs_item["percentage"]) for vubs_item in vubs]


    def getSimilaritiesForItems(self, site_id, similarity_type, item_ids):
        c_item_similarities = getSiteDBCollection(self.connection, site_id, 
                "item_similarities_%s" % similarity_type)
        result = []
        for row in c_item_similarities.find({"item_id": {"$in": item_ids}}):
            most_similar_items = row["mostSimilarItems"]
            result.append(most_similar_items)
        return result

    API_KEY2SITE_ID = None
    SITE_ID2API_KEY = None

    def reloadApiKey2SiteID(self):
        self.API_KEY2SITE_ID = {}
        self.SITE_ID2API_KEY = {}
        c_sites = self.connection["tjb-db"]["sites"]
        for site in c_sites.find():
            self.API_KEY2SITE_ID[site["api_key"]] = site["site_id"]
            self.SITE_ID2API_KEY[site["site_id"]] = site["api_key"]

    def getSiteID2ApiKey(self):
        if self.SITE_ID2API_KEY is None:
            self.reloadApiKey2SiteID()
        return self.SITE_ID2API_KEY

    def getApiKey2SiteID(self):
        if self.API_KEY2SITE_ID is None:
            self.reloadApiKey2SiteID()
        return self.API_KEY2SITE_ID


    def loadSites(self):
        c_sites = self.connection["tjb-db"]["sites"]
        return [site for site in c_sites.find()]


    # FIXME; should also make the api_key field unique.
    def generateApiKey(self, site_id, site_name):
        c_sites = self.connection["tjb-db"]["sites"]
        api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
        while c_sites.find_one({"api_key": api_key}) is not None:
            api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
        return api_key


    def updateSite(self, site_id, site_name, calc_interval):
        c_sites = self.connection["tjb-db"]["sites"]
        site = c_sites.find_one({"site_id": site_id})
        if site is None:
            if site_name is None:
                raise UpdateSiteError("site_name is required for new site creation.")
            site = {"site_id": site_id}
        site.setdefault("last_update_ts", None)
        site.setdefault("disabledFlows", [])
        site.setdefault("api_key", self.generateApiKey())
        if site_name is not None:
            site["site_name"] = site_name
        site["calc_interval"] = calc_interval
        c_sites.save(site)


    def updateItem(self, site_id, item):
        c_items = getSiteDBCollection(self.connection, site_id, "items")
        item_in_db = c_items.find_one({"item_id": item["item_id"]})
        if item_in_db is None:
            item_in_db = {}
        else:
            item_in_db = {"_id": item_in_db["_id"]}
        item_in_db.update(item)
        item_in_db["available"] = True
        c_items.save(item_in_db)


    def removeItem(self, site_id, item_id):
        c_items = getSiteDBCollection(self.connection, site_id, "items")
        item_in_db = c_items.find_one({"item_id": item_id})
        if item_in_db is not None:
            item_in_db["available"] = False
            c_items.save(item_in_db)


    def getItem(self, site_id, item_id):
        c_items = getSiteDBCollection(self.connection, site_id, "items")
        return c_items.find_one({"item_id": item_id})

    def convertTopNFormat(self, site_id, req_id, topn, amount, include_item_info=True, 
            url_converter=None):
        if url_converter is None:
            url_converter = self.getRedirectUrlFor
        c_items_collection = getSiteDBCollection(self.connection, site_id, "items")
        result = []
        for topn_row in topn:
            item_in_db = c_items_collection.find_one({"item_id": topn_row[0]})
            if item_in_db is None or item_in_db["available"] == False:
                    continue
            if include_item_info:
                del item_in_db["_id"]
                del item_in_db["available"]
                item_in_db["score"] = topn_row[1]
                item_in_db["item_link"] = url_converter(item_in_db["item_link"], site_id, 
                                                item_in_db["item_id"], req_id)
                result.append(item_in_db)
            else:
                result.append({"item_id": topn_row[0], "score": topn_row[1]})
            if len(result) == amount:
                break
        return result


    def calc_weighted_top_list_method1(self, site_id, similarity_type, 
            items_list, extra_excludes_list=[]):
        if len(items_list) > 15:
            recent_history = items_list[:15]
        else:
            recent_history = items_list

        excludes_set = set(items_list + extra_excludes_list)

        # calculate weighted top list from recent browsing history
        rec_map = {}
        for recommended_items in self.getSimilaritiesForItems(site_id, similarity_type, recent_history):
            for rec_item, score in recommended_items:
                if rec_item not in excludes_set:
                    rec_map.setdefault(rec_item, [0,0])
                    rec_map[rec_item][0] += float(score)
                    rec_map[rec_item][1] += 1
        rec_tuples = []
        for key in rec_map.keys():
            score_total, count = rec_map[key][0], rec_map[key][1]
            rec_tuples.append((key, score_total / count))
        rec_tuples.sort(lambda a,b: sign(b[1] - a[1]))
        return [rec_tuple for rec_tuple in rec_tuples]


    def recommend_based_on_some_items(self, site_id, similarity_type, items_list):
        topn = self.calc_weighted_top_list_method1(site_id, similarity_type, items_list)
        return topn


    def recommend_based_on_shopping_cart(self, site_id, user_id, shopping_cart):
        if user_id == "null":
            purchasing_history = []
        else:
            purchasing_history = self.getPurchasingHistory(site_id, user_id)["purchasing_history"]
        topn = self.calc_weighted_top_list_method1(site_id, "BuyTogether", shopping_cart,
                    extra_excludes_list=purchasing_history)
        return topn


    # Logging Part
    def writeLogToMongo(self, site_id, content):
        c_raw_logs = getSiteDBCollection(self.connection, site_id, "raw_logs")
        c_raw_logs.ensure_index([("timestamp", pymongo.DESCENDING)])
        c_raw_logs.insert(content)

