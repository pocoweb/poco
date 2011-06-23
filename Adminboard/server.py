#!/usr/bin/env python
import getopt
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

from site_utils import generateApiKey


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


import re

class BaseSiteHandler(tornado.web.RequestHandler):
    def _checkSiteIdValid(self, site_id):
        return re.match("[A-Za-z0-9_]+$", site_id) is not None

    def _checkCalcIntervalValid(self, calc_interval):
        return re.match("[0-9]+$", calc_interval) is not None

    def _formatDisabledFlows(self, disabledFlows):
        return ",".join(disabledFlows)

    def _parseDisabledFlows(self, disabledFlows):
        return [flow.strip() for flow in disabledFlows.split(",")]


class AddSiteHandler(BaseSiteHandler):
    def get(self):
        self.render("templates/edit_site.html", is_add_site=True, data={})

    def addSite(self, site_id, site_name, calc_interval, disabledFlows):
        connection = pymongo.Connection(settings.mongodb_host)
        site = {"site_id": site_id,
                "last_update_ts": None,
                "disabledFlows": disabledFlows,
                "api_key": generateApiKey(connection, site_id, site_name),
                "site_name": site_name,
                "calc_interval": calc_interval}
        connection["tjb-db"]["sites"].save(site)

    def _checkSiteIdAvailable(self, site_id):
        connection = pymongo.Connection(settings.mongodb_host)
        return connection["tjb-db"]["sites"].find_one({"site_id": site_id}) is None

    def post(self):
        arguments = self.request.arguments
        if not arguments.has_key("site_id") \
            or not arguments.has_key("site_name") \
            or not arguments.has_key("calc_interval"):
            self.write("missing arguments")
        else:
            site_id =   arguments["site_id"][0]
            site_name = arguments["site_name"][0]
            calc_interval = arguments["calc_interval"][0]
            disabledFlowsFormatted = arguments.get("disabledFlows", [""])[0]

            if not self._checkSiteIdValid(site_id):
                self.write("site_id is not valid")
                return
            elif not self._checkSiteIdAvailable(site_id):
                self.write("site_id already in use.")
                return
            elif not self._checkCalcIntervalValid(calc_interval):
                self.write("calc_interval is not valid.")
                return

            disabledFlows = self._parseDisabledFlows(disabledFlowsFormatted)
            self.addSite(site_id, site_name, calc_interval, disabledFlows)

            self.redirect("/edit_site?site_id=%s" % site_id)


class EditSiteHandler(BaseSiteHandler):
    def _getSite(self, site_id):
        connection = pymongo.Connection(settings.mongodb_host)
        return connection["tjb-db"]["sites"].find_one({"site_id": site_id})

    def get(self):
        site_id = self.request.arguments["site_id"][0]
        if not self._checkSiteIdValid(site_id):
            self.write("site_id is not valid")
            return
        site = self._getSite(site_id)
        site["disabledFlowsFormatted"] = self._formatDisabledFlows(site["disabledFlows"])
        self.render("templates/edit_site.html", is_add_site=False, data=site)

    def _updateSite(self, site_id, site_name, calc_interval, disabledFlows):
        connection = pymongo.Connection(settings.mongodb_host)
        site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
        site["site_name"] = site_name
        site["calc_interval"] = calc_interval
        site["disabledFlows"] = disabledFlows
        connection["tjb-db"]["sites"].save(site)

    def post(self):
        arguments = self.request.arguments
        if not arguments.has_key("site_id") \
            or not arguments.has_key("site_name") \
            or not arguments.has_key("calc_interval"):
            self.write("missing arguments")
        else:
            site_id =   arguments["site_id"][0]
            site_name = arguments["site_name"][0]
            calc_interval = arguments["calc_interval"][0]
            disabledFlowsFormatted = arguments.get("disabledFlowsFormatted", [""])[0]

            if not self._checkSiteIdValid(site_id):
                self.write("site_id is not valid")
                return
            elif not self._checkCalcIntervalValid(calc_interval):
                self.write("calc_interval is not valid.")
                return
            
            self._updateSite(site_id, site_name, calc_interval, 
                    self._parseDisabledFlows(disabledFlowsFormatted))

            self.redirect("/edit_site?site_id=%s" % site_id)

app_settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static")
}


handlers = [
    (r"/", IndexHandler),
    (r"/ajax/calcAsap",  RunCalculationHandler),
    (r"/ajax/loadData",  AjaxLoadDataHandler),
    (r"/add_site", AddSiteHandler),
    (r"/edit_site", EditSiteHandler)
]


def main():
    opts, _ = getopt.getopt(sys.argv[1:], 'p:', ['port='])
    port = settings.server_port
    for o, p in opts:
        if o in ['-p', '--port']:
            try:
                port = int(p)
            except ValueError:
                print "port should be integer"
    application = tornado.web.Application(handlers, **app_settings)
    application.listen(port, settings.server_name)
    print "Listen at %s:%s" % (settings.server_name, port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
