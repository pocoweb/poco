#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
import httplib
import time
import datetime
import urlparse
import pymongo
from common.utils import getSiteDBCollection
from ApiServer.mongo_client import MongoClient
import settings


MONGODB_HOST = settings.mongodb_host

connection = pymongo.Connection(MONGODB_HOST)

mongo_client = MongoClient(connection)


# http://www.voidspace.org.uk/python/articles/urllib2.shtml


def checkUrl(url):
    pr = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(pr.netloc)
    conn.request("HEAD", pr.path)
    res = conn.getresponse()
    return res.status


def writeLog(f_log, line):
    print >>f_log, line
    f_log.flush()

def removeItem(f_log, site_id, item_id):
    writeLog(f_log, "removeItem(%s)" % item_id)
    mongo_client.removeItem(site_id, item_id)


def getCurrentTime():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# TODO: limit the checking time. 
if __name__ == "__main__":
    while True:
        for site_id in settings.site_ids:
            f_log = open(settings.log_file_path, "a")
            writeLog(f_log, "%s: Begin checking for %s" % (getCurrentTime(), site_id))
            c_items = getSiteDBCollection(connection, site_id, "items")
            items_list = [item for item in c_items.find({"available": True})]
            items_count = len(items_list)
            t1 = time.time()
            for item_idx in range(len(items_list)):
                item = items_list[item_idx]
                if item_idx % 50 == 0:
                    writeLog(f_log, "%s: Progress: %2d%%" % (getCurrentTime(), item_idx / float(items_count) * 100))
                if str(checkUrl(item["item_link"])) == "404":
                    removeItem(f_log, site_id, item["item_id"])
            t2 = time.time()
            writeLog(f_log, "%s: Finish checking for %s in %s seconds." % (getCurrentTime(), site_id, (t2 - t1)))
            writeLog(f_log, "%s: Go Sleep for 8 hours " % getCurrentTime())
            f_log.close()
        time.sleep(8 * 3600)
