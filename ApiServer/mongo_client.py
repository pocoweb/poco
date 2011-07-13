import pymongo
import hashlib
import urllib
import random
import time

from common.utils import getSiteDBName
from common.utils import getSiteDBCollection
from common.utils import sign


class UpdateSiteError(Exception):
    pass


class SimpleRecommendationResultFilter:
    def is_allowed(self, item_dict):
        return item_dict["available"]

# Now we intepret items which do not belong to any group in a default group.
class SameGroupRecommendationResultFilter:
    def __init__(self, mongo_client, site_id, item_id):
        self.mongo_client = mongo_client
        self.site_id = site_id
        self.item_id = item_id

        category_groups = mongo_client.getCategoryGroups(site_id)
        allowed_category_groups = []
        item = mongo_client.getItem(site_id, item_id)
        if item is not None:
            for category in item["categories"]:
                category_group = category_groups.get(category, None)
                allowed_category_groups.append(category_group)
            self.allowed_categories = set(item["categories"])
            self.allowed_category_groups = set(allowed_category_groups)
        else:
            self.allowed_categories = set([])
            self.allowed_category_groups = set([])
        
    def is_allowed(self, item_dict):
        if not item_dict["available"]:
            return False
        category_groups = self.mongo_client.getCategoryGroups(self.site_id)
        if len(item_dict["categories"]) == 0:
            return True
        else:
            for category in item_dict["categories"]:
                if category_groups is not None:
                    item_category_group = category_groups.get(category, None)
                    if item_category_group in self.allowed_category_groups:
                        return True
                elif category in self.allowed_categories:
                    return True
            return False


class MongoClient:
    def __init__(self, connection):
        self.connection = connection

    def toggle_black_list(self, site_id, item_id1, item_id2, is_on):
        c_rec_black_lists = getSiteDBCollection(self.connection, site_id, "rec_black_lists")
        rec_black_list = c_rec_black_lists.find_one({"item_id": item_id1})
        if rec_black_list is None:
            c_rec_black_lists.insert({"item_id": item_id1, "black_list": []})
        if is_on:
            c_rec_black_lists.update({"item_id": item_id1}, {"$addToSet": {"black_list": item_id2}})
        else:
            c_rec_black_lists.update({"item_id": item_id1}, {"$pull":  {"black_list": item_id2}})


    def get_black_list(self, site_id, item_id):
        c_rec_black_lists = getSiteDBCollection(self.connection, site_id, "rec_black_lists")
        rec_black_list = c_rec_black_lists.find_one({"item_id": item_id})
        if rec_black_list is None:
            return []
        else:
            return rec_black_list["black_list"]

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
        c_item_similarities = getSiteDBCollection(self.connection, site_id, "item_similarities_%s" % similarity_type)
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


    def updateCategory(self, site_id, category):
        c_categories = getSiteDBCollection(self.connection, site_id, "categories")
        cat_in_db = c_categories.find_one({"category_id": category["category_id"]})
        if cat_in_db is None:
            cat_in_db = {}
        else:
            cat_in_db = {"_id": cat_in_db["_id"]}
        cat_in_db.update(category)
        c_categories.save(cat_in_db)


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

    def reloadCategoryGroups(self, site_id):
        now = time.time()
        c_sites = self.connection["tjb-db"]["sites"]
        site = c_sites.find_one({"site_id": site_id})
        self.SITE_ID2CATEGORY_GROUPS[site_id] = (site.get("category_groups", {}), now)


    SITE_ID2CATEGORY_GROUPS = {}
    def getCategoryGroups(self, site_id):
        # TODO: use callLater to update allowed_cross_category
        allowed_cross_category, last_update_ts = self.SITE_ID2CATEGORY_GROUPS.get(site_id, (None, None))
        now = time.time()
        if not self.SITE_ID2CATEGORY_GROUPS.has_key(site_id) \
            or self.SITE_ID2CATEGORY_GROUPS[site_id][1] - now > 10:
            self.reloadCategoryGroups(site_id)
        return self.SITE_ID2CATEGORY_GROUPS[site_id][0]


    def convertTopNFormat(self, site_id, req_id, result_filter, topn, amount, include_item_info=True, 
            url_converter=None, excluded_recommendation_items=set([])):
        if url_converter is None:
            url_converter = self.getRedirectUrlFor
        c_items_collection = getSiteDBCollection(self.connection, site_id, "items")
        result = []
        
        for topn_row in topn:
            item_in_db = c_items_collection.find_one({"item_id": topn_row[0]})
            if item_in_db is None or not result_filter.is_allowed(item_in_db) \
                or item_in_db["item_id"] in excluded_recommendation_items:
                    continue
            if include_item_info:
                del item_in_db["_id"]
                del item_in_db["available"]
                del item_in_db["categories"]
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

