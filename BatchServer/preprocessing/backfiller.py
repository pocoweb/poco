import sys
import time
import logging
import pymongo
from common import utils
import simplejson as json


logger = logging.getLogger("Backfiller")




class BackFiller:
    def __init__(self, site_id, last_ts, output_file_path):
        connection = pymongo.Connection()
        self.raw_logs = utils.getSiteDBCollection(connection, site_id, "raw_logs")
        self.last_ts = last_ts
        self.output_file_path = output_file_path
        self.tjbid2user = {}

    # TODO: maybe use atomic update later?
    def workOnDoc(self, log_doc, is_old_region):
        if not is_old_region and log_doc["user_id"] != "null":
            self.tjbid2user[log_doc["tjbid"]] = log_doc["user_id"]
        if log_doc.get("filled_user_id", None) is None \
            or log_doc["filled_user_id"].startswith("ANO_"):
            if log_doc["user_id"] == "null":
                if self.tjbid2user.has_key(log_doc["tjbid"]):
                    log_doc["filled_user_id"] = self.tjbid2user[log_doc["tjbid"]]
                else:
                    log_doc["filled_user_id"] = "ANO_" + log_doc["tjbid"]
            else:
                log_doc["filled_user_id"] = log_doc["user_id"]
            self.raw_logs.save(log_doc)
        del log_doc["_id"]
        self.f_output.write("%s\n" % json.dumps(log_doc))
        self.f_output.flush()

    # TODO: start a cursor every 200000 entries?
    def start(self):
        self.f_output = open(self.output_file_path, "w")
        latest_ts_this_time = None
        is_old_region = False
        t0 = time.time()
        count = 0
        for log_doc in self.raw_logs.find().sort("timestamp", -1):
            count += 1
            if count % 10000 == 0:
                logger.info("Count: %s, %s rows/sec" % (count, count/(time.time() - t0)))

            if self.last_ts is not None and log_doc["timestamp"] == last_ts:
                is_old_region = True
            if latest_ts_this_time is None:
                latest_ts_this_time = log_doc["timestamp"]
            self.workOnDoc(log_doc, is_old_region)
        if latest_ts_this_time is not None:
            return latest_ts_this_time
        else:
            return self.last_ts
        self.f_output.close()


