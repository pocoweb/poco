#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
import os
import time
import tornado.ioloop
import tornado.web
import simplejson as json
import pymongo

import settings
from ApiServer import mongo_client
from common.utils import getSiteDBCollection


def convertSecondsAsHoursMinutesSeconds(seconds):
    seconds = int(seconds)
    hours = seconds / 3600
    a = seconds % 3600
    minutes = a / 60
    seconds_remain = a % 60
    result_str = ""
    if hours > 0:
        result_str += "%s hours " % hours
    if minutes > 0:
        result_str += "%s minutes " % minutes
    result_str += "%s seconds" % seconds_remain
    return result_str



def getSiteInfos():
    connection = pymongo.Connection(settings.mongodb_host)
    sites = mongo_client.loadSites()
    result = []
    for site in sites:
        sci = {"site_id": site["site_id"], "site_name": site["site_name"], "disabledFlows": site.get("disabledFlows", [])}
        calculation_records = getSiteDBCollection(connection, site["site_id"], "calculation_records")
        records = [row for row in calculation_records.find().sort("begin_timestamp", -1).limit(1)]
        if records == []:
            sci["status"] = "NEVER_CALC"
        else:
            record = records[0]
            sci["last_calculation_id"] = record["calculation_id"]
            if record.has_key("end_timestamp"):
                if record["is_successful"]:
                    sci["status"] = "SUCCESSFUL"
                    sci["since_last"] = convertSecondsAsHoursMinutesSeconds(time.time() - record["end_timestamp"])
                    sci["time_spent"] = convertSecondsAsHoursMinutesSeconds(record["end_timestamp"] - record["begin_timestamp"])
                    est_next_run = max(record["end_timestamp"] + site["calc_interval"] - time.time(), 0)
                    if est_next_run == 0:
                        sci["est_next_run"] = "as soon as possible"
                    else:
                        sci["est_next_run"] = convertSecondsAsHoursMinutesSeconds(est_next_run)
                else:
                    sci["status"] = "FAILED"
                    sci["since_last"] = convertSecondsAsHoursMinutesSeconds(time.time() - record["end_timestamp"])
                    sci["time_spent"] = convertSecondsAsHoursMinutesSeconds(record["end_timestamp"] - record["begin_timestamp"])
                    est_next_run = max(record["end_timestamp"] + site["calc_interval"] - time.time(), 0)
                    if est_next_run == 0:
                        sci["est_next_run"] = "as soon as possible"
                    else:
                        sci["est_next_run"] = convertSecondsAsHoursMinutesSeconds(est_next_run)
            else:
                sci["status"] = "RUNNING"
                sci["time_spent"] = convertSecondsAsHoursMinutesSeconds(time.time() - record["begin_timestamp"])

        manual_calculation_list = connection["tjb-db"]["manual_calculation_list"]
        manual_calculation_request = manual_calculation_list.find_one({"site_id": site["site_id"]})
        if manual_calculation_request is not None:
            request_timestamp = manual_calculation_request["request_timestamp"]
            sci["request_waiting_time"] = convertSecondsAsHoursMinutesSeconds(time.time() - request_timestamp)

        result.append(sci)

    return result


class AjaxLoadDataHandler(tornado.web.RequestHandler):
    def get(self):
        self.write(json.dumps(getSiteInfos()))


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        #sites = getSiteInfos()
        self.render("templates/index.html")

def scheduleCalculation(site_id):
    connection = pymongo.Connection(settings.mongodb_host)
    manual_calculation_list = connection["tjb-db"]["manual_calculation_list"]
    record_in_db = manual_calculation_list.find_one({"site_id": site_id})
    if record_in_db is None:
        manual_calculation_list.insert({"site_id": site_id, "request_timestamp": time.time()})


class RunCalculationHandler(tornado.web.RequestHandler):
    def get(self):
        site_id = self.request.arguments["site_id"][0]
        scheduleCalculation(site_id)
        self.write('{"code": 0}')


app_settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static")
}


handlers = [
    (r"/", IndexHandler),
    (r"/ajax/calcAsap",  RunCalculationHandler),
    (r"/ajax/loadData",  AjaxLoadDataHandler)
]


def main():
    application = tornado.web.Application(handlers, **app_settings)
    application.listen(settings.server_port, settings.server_name)
    print "Listen at %s:%s" % (settings.server_name, settings.server_port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
