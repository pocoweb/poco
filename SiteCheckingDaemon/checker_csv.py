#coding=utf-8
import logging
from common.utils import getSiteDBCollection
from utils import getCurrentTime


logger = logging.getLogger("Checker_csv")

import urllib2
def open_csv():
    request = urllib2.Request('http://www.kuaishubao.com/product.xls')
    opener = urllib2.build_opener()
    resp = opener.open(request)
    last = open("../../temp/kuaishubao.last", "w+")
    last_modified = last.read()
    logger.info("Last-Modified saved:" + last_modified)
    resp_last_modified = resp.headers.get('Last-Modified')
    logger.info("Last-Modified resp:" + resp_last_modified)
    if last_modified.strip() != resp_last_modified.strip():
        lines = resp.readlines()
        last.write(resp_last_modified)
    else:
        lines = []
    last.close()
    return lines

def check(site_id, mongo_client):
    # TODO, disable and enable seperately
    items = getSiteDBCollection(mongo_client.connection, site_id, "items")
    items.update({}, {"$set":{"available":False}}, multi=True)
    #f = open("../../temp/product.csv", "r")
    #for line in f:
    lines = open_csv()
    for line in lines:
        try:
            _id = int(line.strip())
            items.update({"item_id":str(_id)}, {"$set":{"available":True}})
        except ValueError:
            pass

