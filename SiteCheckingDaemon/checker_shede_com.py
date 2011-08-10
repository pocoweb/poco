#coding=utf-8
import logging
from common.utils import getSiteDBCollection
from utils import getCurrentTime


logger = logging.getLogger("Checker_404")


def check(site_id, mongo_client):
    c_items = getSiteDBCollection(mongo_client.connection, site_id, "items")
    items_cur = c_items.find({"item_name": {"$regex": "已定", "$options": "i"},"available": True})
    items_count = items_cur.count()
    logger.info("%s items to disable." % items_count)
    c_items.update({"item_name": {"$regex": "已定", "$options": "i"},"available": True},
                   {"$set": {"available": False}}, multi=True)
