SITE_ID = "tester"

items = {
            "1": {"site_id": SITE_ID, "item_id": "1",
                  "item_link": "http://example.com/item?id=1",
                  "item_name": "Turk"},
            "3": {"site_id": SITE_ID, "item_id": "3", 
             "item_link": "http://example.com/item?id=3",
             "item_name": "Harry Potter I"},
            "2": {"site_id": SITE_ID, "item_id": "2", 
             "item_link": "http://example.com/item?id=2",
             "item_name": "Lord of Ring I"},
            "8": {"site_id": SITE_ID, "item_id": "8", 
             "item_link": "http://example.com/item?id=8",
             "item_name": "Best Books"},
            "11": {"site_id": SITE_ID, "item_id": "11", 
             "item_link": "http://example.com/item?id=11",
             "item_name": "Meditation"},
             "15": {"site_id": SITE_ID, "item_id": "15", 
             "item_link": "http://example.com/item?id=15",
             "item_name": "SaaS Book"},
             "17": {"site_id": SITE_ID, "item_id": "17", 
             "item_link": "http://example.com/item?id=17",
             "item_name": "Who am I"},
             "21": {"site_id": SITE_ID, "item_id": "21", 
             "item_link": "http://example.com/item?id=21",
             "item_name": "Kill A Bird"},
             "29": {"site_id": SITE_ID, "item_id": "29", 
             "item_link": "http://example.com/item?id=29",
             "item_name": "Soo..."}
        }


import pymongo
import settings


def getApiKey(site_id):
    connection = pymongo.Connection(settings.mongodb_host)
    return connection["tjb-db"]["sites"].find_one({"site_id": site_id})["api_key"]

for item in items.values():
    item["api_key"] = getApiKey(item["site_id"])
    del item["site_id"]
