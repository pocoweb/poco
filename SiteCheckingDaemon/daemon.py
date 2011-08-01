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


# This script is "kuaishubao" only at this time.
SITE_ID = "kuaishubao"


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


def removeItem(item_id):
    print "removeItem(%s)" % item_id
    mongo_client.removeItem(SITE_ID, item_id)


if __name__ == "__main__":
    while True:
        f = open("/tmp/BEGIN_AT", "w")
        f.write("Begin checking at %s" % datetime.datetime.now())
        f.close()
        print "Begin checking at %s" % datetime.datetime.now()
        c_items = getSiteDBCollection(connection, SITE_ID, "items")
        items_list = [item for item in c_items.find({"available": True})]
        items_count = len(items_list)
        t1 = time.time()
        for item_idx in range(len(items_list)):
            item = items_list[item_idx]
            if item_idx % 50 == 0:
                print "Progress: %2d%%" % (item_idx / float(items_count) * 100)
            if str(checkUrl(item["item_link"])) == "404":
                removeItem(item["item_id"])
        t2 = time.time()
        print "Finish checking at %s, in %s seconds." % (datetime.datetime.now(), (t2 - t1))
        f = open("/tmp/END_AT", "w")
        f.write("Finish checking at %s, in %s seconds." % (datetime.datetime.now(), (t2 - t1)))
        f.close()
        print "Go Sleep for 8 hours "	
        time.sleep(8 * 3600)
