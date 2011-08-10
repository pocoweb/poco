import logging
import httplib
import urlparse
from common.utils import getSiteDBCollection
from utils import getCurrentTime


logger = logging.getLogger("Checker_404")


def checkUrl(url):
    pr = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(pr.netloc)
    conn.request("HEAD", pr.path)
    res = conn.getresponse()
    return res.status


def removeItem(mongo_client, site_id, item_id):
    logger.info("removeItem(%s)" % item_id)
    mongo_client.removeItem(site_id, item_id)


def check(site_id, mongo_client):
    c_items = getSiteDBCollection(mongo_client.connection, site_id, "items")
    items_cur = c_items.find({"available": True})
    items_count = items_cur.count()
    item_idx = 0
    for item in items_cur:
        item_idx += 1
        if item_idx % 50 == 0:
            logger.info("%s: Progress: %2d%%" % (getCurrentTime(), item_idx / float(items_count) * 100))
        if str(checkUrl(item["item_link"])) == "404":
            removeItem(mongo_client, site_id, item["item_id"])

