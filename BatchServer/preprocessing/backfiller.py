import sys
import time
import logging
from common import utils
import simplejson as json


class BackFiller:
    def __init__(self, connection, site_id, last_ts, output_file_path):
        self.connection = connection
        self.site_id = site_id
        self.raw_logs = utils.getSiteDBCollection(connection, site_id, "raw_logs")
        self.c_tmp_user_identified_logs_plo = utils.getSiteDBCollection(connection, site_id, "tmp_user_identified_logs_plo")
        self.last_ts = last_ts
        self.output_file_path = output_file_path
        self.tjbid2user = {}

    def dateTimeAsFloat(self, datetime):
        return time.mktime(datetime.timetuple()) + datetime.microsecond / 1000000.0

    def _updateFilledUserId(self, log_doc, new_value):
        if log_doc.has_key("filled_user_id") \
            and log_doc["filled_user_id"].startswith("ANO_") \
            and not new_value.startswith("ANO_"):
            if log_doc["behavior"] == "PLO":
                self.c_tmp_user_identified_logs_plo.insert({"log_id": log_doc["_id"]})
        log_doc["filled_user_id"] = new_value

    # TODO: maybe use atomic update later?
    def workOnDoc(self, log_doc, is_old_region):
        if log_doc.has_key("tjbid"):
            user_id = log_doc.get("user_id", "null")
            if not is_old_region and user_id != "null":
                self.tjbid2user[log_doc["tjbid"]] = user_id
            if log_doc.get("filled_user_id", None) is None \
                or log_doc["filled_user_id"].startswith("ANO_"):
                if user_id == "null":
                    if self.tjbid2user.has_key(log_doc["tjbid"]):
                        self._updateFilledUserId(log_doc, self.tjbid2user[log_doc["tjbid"]])
                    else:
                        self._updateFilledUserId(log_doc, "ANO_" + log_doc["tjbid"])
                else:
                    self._updateFilledUserId(log_doc, user_id)
                self.raw_logs.save(log_doc)
            del log_doc["_id"]
            log_doc["created_on"] = self.dateTimeAsFloat(log_doc["created_on"])
            self.f_output.write("%s\n" % json.dumps(log_doc))
            self.f_output.flush()

    # TODO: start a cursor every 200000 entries?
    # We use find(timeout=False) here and use "del cursor" to close it.
    # see http://stackoverflow.com/questions/5392318/how-to-close-cursor-in-mongokit
    def start(self):
        logger = logging.getLogger("Backfiller")
        self.f_output = open(self.output_file_path, "w")
        latest_ts_this_time = None
        is_old_region = False
        t0 = time.time()
        count = 0
        cursor = self.raw_logs.find(timeout=False).sort("created_on", -1)
        try:
            for log_doc in cursor:
                count += 1
                if count % 10000 == 0:
                    logger.info("Count: %s, %s rows/sec" % (count, count/(time.time() - t0)))

                # TODO use log_doc["created_on"] == last_ts or  >=
                if self.last_ts is not None and log_doc["created_on"] == last_ts:
                    is_old_region = True
                if latest_ts_this_time is None:
                    latest_ts_this_time = log_doc["created_on"]
                self.workOnDoc(log_doc, is_old_region)
            if latest_ts_this_time is not None:
                return latest_ts_this_time
            else:
                return self.last_ts
        finally:
            self.f_output.close()
            del cursor

