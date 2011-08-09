#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
import time
import pymongo
import logging

from ApiServer.mongo_client import MongoClient
from utils import getCurrentTime
import settings

import checker_404
import checker_shede_com


def getMongoClient():
    MONGODB_HOST = settings.mongodb_host
    connection = pymongo.Connection(MONGODB_HOST)
    return MongoClient(connection)


logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
                    datefmt="%Y-%m-%d %I:%M:%S",
                    filename=settings.log_file_path,
                    filemode='a')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(name)s|%(message)s")
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# http://www.voidspace.org.uk/python/articles/urllib2.shtml

logger = logging.getLogger("daemon")

site_id2checker = {
    "kuaishubao": checker_404,
    "shede_com": checker_shede_com
    }

# TODO: limit the checking time. 
if __name__ == "__main__":
    while True:
        mongo_client = getMongoClient()
        try:
            for site_id in settings.site_ids:
                logger.info("%s: Begin checking for %s" % (getCurrentTime(), site_id))
                t1 = time.time()
                checker = site_id2checker.get(site_id, None)
                if checker is not None:
                    site_id2checker[site_id].check(site_id, mongo_client)
                else:
                    logger.critical("checker for '%s' not found." % site_id)
                t2 = time.time()
                logger.info("%s: Finish checking for %s in %s seconds." % (getCurrentTime(), site_id, (t2 - t1)))
                logger.info("%s: Go Sleep for 8 hours " % getCurrentTime())
        finally:
            mongo_client.connection.disconnect()
            del mongo_client
        time.sleep(8 * 3600)
