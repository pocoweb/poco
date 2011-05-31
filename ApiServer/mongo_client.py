import pymongo
import md5


connection = pymongo.Connection()


cache = {}
def getCachedVAV(site_id, history_item):
    global cache
    if not cache.has_key((site_id, history_item)):
        cache[(site_id, history_item)] = recommend_viewed_also_view(site_id, str(history_item), 15)
    return cache[(site_id, history_item)]


def recommend_viewed_also_view(site_id, item_id, amount):
    item_similarities = connection["tjb_%s" % site_id]["item_similarities"]
    result = item_similarities.find_one({"item_id": item_id})
    most_similar_items = result["mostSimilarItems"]
    if len(most_similar_items) > amount:
        topn = most_similar_items[:amount]
    else:
        topn = most_similar_items
    return topn


def getSimilaritiesForItems(site_id, item_ids):
    item_similarities = connection["tjb_%s" % site_id]["item_similarities"]
    result = []
    for row in item_similarities.find({"item_id": {"$in": item_ids}}):
        most_similar_items = row["mostSimilarItems"]
        result.append(most_similar_items)
    return result


sites = connection["tjb-db"]["sites"]
SITE_IDS = None
def reloadSiteIds():
    global SITE_IDS
    site_ids = [site["site_id"] for site in sites.find()]
    SITE_IDS = set(site_ids)


def getSiteIds():
    global SITE_IDS
    if SITE_IDS is None:
        reloadSiteIds()
    return SITE_IDS


def updateSite(site_id, site_name):
    site = sites.find_one({"site_id": site_id})
    if site is None:
        site = {"site_id": site_id}
    site["site_name"] = site_name
    sites.save(site)


def updateItem(site_id, item):
    items = connection["tjb_%s" % site_id]["items"]
    item_in_db = items.find_one({"item_id": item["item_id"]})
    if item_in_db is None:
        item_in_db = {}
    item_in_db.update(item)
    item_in_db["available"] = True
    items.save(item_in_db)


def removeItem(site_id, item_id):
    items = connection["tjb_%s" % site_id]["items"]
    item_in_db = items.find_one({"item_id": item_id})
    if item_in_db is not None:
        item_in_db["available"] = False
        items.save(item_in_db)


def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def calc_weighted_top_list_method1(site_id, browsing_history):
    if len(browsing_history) > 15:
        recent_history = browsing_history[:15]
    else:
        recent_history = browsing_history

    # calculate weighted top list from recent browsing history
    rec_map = {}
    #for history_item in recent_history:
    #    #recommended_items = recommend_viewed_also_view(site_id, str(history_item), 15)
    #    recommended_items = getCachedVAV(site_id, str(history_item))
    for recommended_items in getSimilaritiesForItems(site_id, recent_history):
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
    return [int(rec_tuple[0]) for rec_tuple in rec_tuples]


def recommend_based_on_browsing_history(site_id, browsing_history, amount):
    topn = calc_weighted_top_list_method1(site_id, browsing_history) 
    if len(topn) > amount:
        topn = topn[:amount]
    return topn
