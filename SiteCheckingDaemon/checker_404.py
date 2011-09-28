import logging
import httplib
import urlparse
import socket
from common.utils import getSiteDBCollection
from utils import getCurrentTime


logger = logging.getLogger("Checker_404")


def checkUrl(url):
    pr = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(pr.netloc)
    try:
        conn.request("HEAD", pr.path)
    except socket.error:
        logger.error("Failed to access %s" % url)
        print url
        return None
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
    fail_count = 0
    for item in items_cur:
        item_idx += 1
        if item_idx % 50 == 0:
            logger.info("%s: Progress: %2d%%" % (getCurrentTime(), item_idx / float(items_count) * 100))
        check_status = str(checkUrl(item["item_link"]))  
        if check_status == "404":
            removeItem(mongo_client, site_id, item["item_id"])
        elif check_status == "None":
            fail_count += 1
            if fail_count > 3:
                logger.critical("more than 3 checkUrl failed. ")
                return

