#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
import time
import datetime
import pymongo
import logging
import uuid

from common.utils import getSiteDBCollection
from ApiServer.mongo_client import MongoClient
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


# site_checking_daemon_logs
#{"site_id": "", "checking_id": "", "created_on": "", "ended_on": "", "state": "", "logs": []}
class MongoRecordHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        logging.Handler.__init__(self, level)
        self.site_id = None
        self.checking_id = None
        self.c_site_checking_daemon_logs = None
        self.connection = None

    def beginSiteLogFor(self, connection, site_id):
        self.connection = connection
        self.site_id = site_id
        self.checking_id = str(uuid.uuid4())
        self.c_site_checking_daemon_logs = getSiteDBCollection(self.connection, self.site_id, 
               "site_checking_daemon_logs")
        self.c_site_checking_daemon_logs.insert(
                {"site_id": site_id, "checking_id": self.checking_id,
                 "created_on": datetime.datetime.now(),
                 "state": "RUNNING",
                 "logs": []})
        logging.getLogger('').addHandler(self)

    def endSiteLogAs(self, state):
        logging.getLogger('').removeHandler(self)
        if self.checking_id is not None:
            log = self.c_site_checking_daemon_logs.find_one({"checking_id": self.checking_id})
            log["ended_on"] = datetime.datetime.now()
            log["state"] = state
            self.c_site_checking_daemon_logs.save(log)

        self.site_id = None
        self.checking_id = None

    def emit(self, record):
        msg = self.format(record)
        log = self.c_site_checking_daemon_logs.find_one({"checking_id": self.checking_id})
        log["logs"].append(msg)
        self.c_site_checking_daemon_logs.save(log)

def init_mongo_record_handler():
    mr_handler = MongoRecordHandler()
    mr_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(name)s|%(message)s")
    mr_handler.setFormatter(formatter)
    return mr_handler


# http://www.voidspace.org.uk/python/articles/urllib2.shtml

logger = logging.getLogger("daemon")

site_id2checker = {
    "kuaishubao": checker_404,
    "shede_com": checker_shede_com,
    "crucco_com": checker_404
    }


class CheckerNotFoundError(Exception):
    pass


# TODO: limit the checking time. 
if __name__ == "__main__":
    mr_handler = init_mongo_record_handler()
    while True:
        mongo_client = getMongoClient()
        try:
            for site_id in settings.site_ids:
                try:
                    checker = site_id2checker.get(site_id, None)
                    if checker is not None:
                        t1 = time.time()
                        mr_handler.beginSiteLogFor(mongo_client.connection, site_id)
                        logger.info("Begin checking for %s:%s" % (site_id, mr_handler.checking_id))
                        site_id2checker[site_id].check(site_id, mongo_client)
                        t2 = time.time()
                        logger.info("Finish checking for %s in %s seconds." % (site_id, (t2 - t1)))
                        mr_handler.endSiteLogAs("SUCC")
                    else:
                        logger.critical("checker for '%s' not found." % site_id)
                        raise CheckerNotFoundError("checker for '%s' not found." % site_id)
                except:
                    logger.critical("Unknown error", exc_info=True)
                    mr_handler.endSiteLogAs("FAIL")
            logger.info("Go Sleep for 8 hours ")
        finally:
            mongo_client.connection.disconnect()
            del mongo_client
        time.sleep(8 * 3600)
