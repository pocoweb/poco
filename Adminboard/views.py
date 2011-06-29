import sys
sys.path.insert(0, "../")
import re
import os.path
import time
import hashlib
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import RequestContext
import pymongo
import simplejson as json
from common.utils import getSiteDBCollection
from common.utils import convertSecondsAsHoursMinutesSeconds

from ApiServer.mongo_client import MongoClient

from site_utils import generateApiKey
import settings


def getConnection():
    return pymongo.Connection(settings.mongodb_host)


mongo_client = MongoClient(getConnection())


def getSiteInfos():
    connection = pymongo.Connection(settings.mongodb_host)
    sites = mongo_client.loadSites()
    result = []
    for site in sites:
        sci = {"site_id": site["site_id"], "site_name": site["site_name"], 
               "disabledFlows": site.get("disabledFlows", [])}
        calculation_records = getSiteDBCollection(connection, site["site_id"], 
                                    "calculation_records")
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

        c_items = getSiteDBCollection(connection, site["site_id"], "items")
        sci["items_count"] = c_items.find().count()

        result.append(sci)

    return result


def scheduleCalculation(site_id):
    connection = pymongo.Connection(settings.mongodb_host)
    c_manual_calculation_list = connection["tjb-db"]["manual_calculation_list"]
    record_in_db = c_manual_calculation_list.find_one({"site_id": site_id})
    print "RID:", record_in_db
    if record_in_db is None:
        c_manual_calculation_list.insert({"site_id": site_id, "request_timestamp": time.time()})


# Following are view functions(or callables)

def login_required(callable):
    def method(request):
        if not request.session.has_key("user_name"):
            return redirect("/login")
        return callable(request)
    return method


@login_required
def ajax_load_data(request):
    return HttpResponse(json.dumps(getSiteInfos()))

@login_required
def index(request):
    return render_to_response("index.html", {"user_name": request.session["user_name"]})

@login_required
def ajax_calc_asap(request):
    site_id = request.GET["site_id"]
    scheduleCalculation(site_id)
    return HttpResponse("{'code': 0}")


class BaseSiteHandler:
    def _checkSiteIdValid(self, site_id):
        return re.match("[A-Za-z0-9_]+$", site_id) is not None

    def _checkCalcIntervalValid(self, calc_interval):
        return re.match("[0-9]+$", calc_interval) is not None

    def _formatDisabledFlows(self, disabledFlows):
        return ",".join(disabledFlows)

    def _parseDisabledFlows(self, disabledFlows):
        return [flow.strip() for flow in disabledFlows.split(",")]


class AddSiteHandler(BaseSiteHandler):
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

    def _handlePOST(self, request):
        arguments = request.POST
        if not arguments.has_key("site_id") \
            or not arguments.has_key("site_name") \
            or not arguments.has_key("calc_interval"):
            return HttpResponse("missing arguments")
        else:
            site_id =   arguments["site_id"]
            site_name = arguments["site_name"]
            calc_interval = arguments["calc_interval"]
            disabledFlowsFormatted = arguments.get("disabledFlows", "")

            if not self._checkSiteIdValid(site_id):
                return HttpResponse("site_id is not valid")
            elif not self._checkSiteIdAvailable(site_id):
                return HttpResponse("site_id already in use.")
            elif not self._checkCalcIntervalValid(calc_interval):
                return HttpResponse("calc_interval is not valid.")

            calc_interval = int(calc_interval)

            disabledFlows = self._parseDisabledFlows(disabledFlowsFormatted)
            self.addSite(site_id, site_name, calc_interval, disabledFlows)

            return HttpResponseRedirect("/edit_site?site_id=%s" % site_id)

    def __call__(self, request):
        if request.method == "GET":
            return render_to_response("edit_site.html", 
                        {"is_add_site": True, "data": {'calc_interval': '43200'}},
                        context_instance=RequestContext(request))
        elif request.method == "POST":
            return self._handlePOST(request)

add_site = login_required(AddSiteHandler())



class EditSiteHandler(BaseSiteHandler):
    def _getSite(self, site_id):
        connection = pymongo.Connection(settings.mongodb_host)
        return connection["tjb-db"]["sites"].find_one({"site_id": site_id})

    def _updateSite(self, site_id, site_name, calc_interval, disabledFlows):
        connection = pymongo.Connection(settings.mongodb_host)
        site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
        site["site_name"] = site_name
        site["calc_interval"] = calc_interval
        site["disabledFlows"] = disabledFlows
        connection["tjb-db"]["sites"].save(site)

    def _handleGET(self, request):
        site_id = request.GET["site_id"]
        if not self._checkSiteIdValid(site_id):
            return HttpResponse("site_id is not valid")
        site = self._getSite(site_id)
        site["disabledFlowsFormatted"] = self._formatDisabledFlows(site["disabledFlows"])
        return render_to_response("edit_site.html", 
                {"is_add_site": False, "data": site},
                context_instance=RequestContext(request))

    def _handlePOST(self, request):
        arguments = request.POST
        if not arguments.has_key("site_id") \
            or not arguments.has_key("site_name") \
            or not arguments.has_key("calc_interval"):
            return HttpResponse("missing arguments")
        else:
            site_id =   arguments["site_id"]
            site_name = arguments["site_name"]
            calc_interval = arguments["calc_interval"]
            disabledFlowsFormatted = arguments.get("disabledFlowsFormatted", [""])

            if not self._checkSiteIdValid(site_id):
                return HttpResponse("site_id is not valid")
            elif not self._checkCalcIntervalValid(calc_interval):
                return HttpResponse("calc_interval is not valid.")

            calc_interval = int(calc_interval)

            self._updateSite(site_id, site_name, calc_interval, 
                    self._parseDisabledFlows(disabledFlowsFormatted))

            return HttpResponseRedirect("/edit_site?site_id=%s" % site_id)

    def __call__(self, request):
        if request.method == "GET":
            return self._handleGET(request)
        elif request.method == "POST":
            return self._handlePOST(request)

edit_site = login_required(EditSiteHandler())


def serve_jquery(request):
    file_path = os.path.join(os.path.dirname(__file__), 'static/jquery-1.6.1.min.js')
    return HttpResponse(open(file_path, "r").read())


# The Login System
def logout(request):
    del request.session["user_name"]
    return redirect("/")


def login(request):
    if request.method == "GET":
        msg = request.GET.get("msg", None)
        return render_to_response("login.html", {"msg": msg}, 
                  context_instance=RequestContext(request))
    else:
        conn = getConnection()
        users = conn["tjb-db"]["admin-users"]
        user_in_db = users.find_one({"user_name": request.POST["name"]})
        login_succ = False
        if user_in_db is not None:
            login_succ = user_in_db["hashed_password"] == hashlib.sha256(request.POST["password"] + user_in_db["salt"]).hexdigest()

        if login_succ:
            request.session["user_name"] = request.POST["name"]
            return redirect("/")
        else:
            return redirect("/login?msg=login_failed")


import copy
def _getCurrentUser(request):
    conn = getConnection()
    if request.session.has_key("user_name"):
        return conn["tjb-db"]["admin-users"].find_one({"user_name": request.session["user_name"]})
    else:
        return None

