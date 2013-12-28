import sys
sys.path.insert(0, "../")
import re
import os.path
import datetime
import random
import hashlib
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.template import RequestContext
import pymongo
import simplejson as json
from common.utils import getSiteDBCollection
from common.utils import convertTimedeltaAsDaysHoursMinutesSeconds

from api.mongo_client import MongoClient

from site_utils import generateApiKey
import settings


def getConnection():
    return pymongo.Connection(settings.mongodb_host)

mongo_client = MongoClient(getConnection())


def fillSiteCheckingDaemonInfo(connection, sci):
    now = datetime.datetime.now()
    c_site_checking_daemon_logs = getSiteDBCollection(connection, sci["site_id"], "site_checking_daemon_logs")
    last_records = [row for row in c_site_checking_daemon_logs.find().sort("created_on", -1).limit(1)]
    
    sci["site_checking_status_msg"] = ""
    if last_records == []:
        sci["site_checking_status"] = "NEVER_CHECKED"
    else:
        last_record = last_records[0]
        sci["site_checking_last_id"] = last_record["checking_id"]
        if last_record["state"] in ("FAIL", "SUCC"):
            sci["site_checking_status"] = last_record["state"]
            sci["site_checking_since_last"] = convertTimedeltaAsDaysHoursMinutesSeconds(now - last_record["ended_on"])
            sci["site_checking_time_spent"] = convertTimedeltaAsDaysHoursMinutesSeconds(last_record["ended_on"] - last_record["created_on"])
        elif last_record["state"] == "RUNNING":
            sci["site_checking_status"] = last_record["state"]
            sci["site_checking_time_spent"] = convertTimedeltaAsDaysHoursMinutesSeconds(now - last_record["created_on"])
        else:
            sci["site_checking_status"] = "UNKNOWN_STATE"
            sci["site_checking_status_msg"] = "unknown state: %s" % last_record["state"]
    


def getSiteInfos():
    connection = mongo_client.connection
    sites = mongo_client.loadSites()
    now = datetime.datetime.now()
    result = []
    for site in sites:
        sci = {"site_id": site["site_id"], "site_name": site["site_name"], 
               "disabledFlows": site.get("disabledFlows", [])}
        fillSiteCheckingDaemonInfo(connection, sci)
        calculation_records = getSiteDBCollection(connection, site["site_id"], 
                                    "calculation_records")
        records = [row for row in calculation_records.find().sort("begin_datetime", -1).limit(1)]
        if records == []:
            sci["status"] = "NEVER_CALC"
        else:
            record = records[0]
            sci["last_calculation_id"] = record["calculation_id"]
            if record.has_key("end_datetime"):
                if record["is_successful"]:
                    sci["status"] = "SUCCESSFUL"
                else:
                    sci["status"] = "FAILED"
                sci["since_last"] = convertTimedeltaAsDaysHoursMinutesSeconds(now - record["end_datetime"])
                sci["time_spent"] = convertTimedeltaAsDaysHoursMinutesSeconds(record["end_datetime"] - record["begin_datetime"])
                est_next_run = max(record["end_datetime"] + datetime.timedelta(seconds=site["calc_interval"]) - now, 
                                   datetime.timedelta(seconds=0))
                if est_next_run == datetime.timedelta(seconds=0):
                    sci["est_next_run"] = "as soon as possible"
                else:
                    sci["est_next_run"] = convertTimedeltaAsDaysHoursMinutesSeconds(est_next_run)
            else:
                sci["status"] = "RUNNING"
                sci["time_spent"] = convertTimedeltaAsDaysHoursMinutesSeconds(now - record["begin_datetime"])

        manual_calculation_list = connection["tjb-db"]["manual_calculation_list"]
        manual_calculation_request = manual_calculation_list.find_one({"site_id": site["site_id"]})
        if manual_calculation_request is not None:
            request_datetime = manual_calculation_request["request_datetime"]
            sci["request_waiting_time"] = convertTimedeltaAsDaysHoursMinutesSeconds(now - request_datetime)

        c_items = getSiteDBCollection(connection, site["site_id"], "items")
        sci["all_items_count"] = c_items.find().count()
        sci["available_items_count"] = c_items.find({"available": True}).count()

        result.append(sci)

    return result


def scheduleCalculation(site_id):
    connection = mongo_client.connection
    c_manual_calculation_list = connection["tjb-db"]["manual_calculation_list"]
    record_in_db = c_manual_calculation_list.find_one({"site_id": site_id})
    if record_in_db is None:
        c_manual_calculation_list.insert({"site_id": site_id, "request_datetime": datetime.datetime.now()})


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


def createRandomPassword(length):
    allowedChars = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNOPQRSTUVWXYZ23456789"
    password = ""
    for i in range(length):
        password += allowedChars[random.randint(0, 256) % len(allowedChars)]
    return password


def createHashedPassword(password):
    salt = createRandomPassword(16)
    hashed_password = hashlib.sha256(password + salt).hexdigest()
    return hashed_password, salt


class BaseUserHandler:
    def _checkUserNameValid(self, user_name):
        return len(user_name) > 3 and re.match("[A-Za-z0-9_]+$", user_name) is not None

    def _checkPasswordValid(self, password):
        return len(password) > 5 and re.match("[A-Za-z0-9_]+$", password) is not None

    def _checkUserNameAvailable(self, user_name):
        connection = mongo_client.connection
        return connection["tjb-db"]["users"].find_one({"user_name": user_name}) is None

    def getSiteIds(self):
        return [site["site_id"] for site in mongo_client.loadSites()]


class AddUserHandler(BaseUserHandler):
    def addUser(self, user_name, password, is_admin, sites):
        print user_name, password, is_admin, sites
        connection = mongo_client.connection
        c_users = connection["tjb-db"]["users"]
        hashed_password, salt = createHashedPassword(password)
        c_users.insert({"user_name": user_name, "hashed_password": hashed_password, "salt": salt,
                            "sites": sites, "is_admin": is_admin})

    def _handlePOST(self, request):
        arguments = request.POST
        if not arguments.has_key("user_name") \
            or not arguments.has_key("password") \
            or not arguments.has_key("password_confirm") \
            or not arguments.has_key("is_admin"):
            return HttpResponse("AddUser: missing arguments")
        else:
            user_name =   arguments["user_name"]
            password = arguments["password"]
            password_confirm = arguments["password_confirm"]
            is_admin = arguments["is_admin"] == "true"
            site_ids = arguments.getlist("site_ids")

            print "ARGUMENTS:", arguments

            if not self._checkUserNameValid(user_name):
                return HttpResponse("Invalid User Name(length of user name should be greater than 3 and only A-Z a-z 0-9 and underscore are permitted.)")
            elif not self._checkUserNameAvailable(user_name):
                return HttpResponse("User name already in use.")
            elif not self._checkPasswordValid(password):
                return HttpResponse("Invalid password(length of password should be greater than 5 and only A-Z a-z 0-9 and underscore are permitted.)")
            elif not password == password_confirm:
                return HttpResponse("password and password(Confirm) do not match.")

            self.addUser(user_name, password, is_admin, site_ids)

            return HttpResponseRedirect("/edit_user?user_name=%s" % user_name)


    def __call__(self, request):
        if request.method == "GET":
            return render_to_response("edit_user.html", 
                        {"is_add_user": True, "data": {'sites': [], 'is_admin': False},
                         "all_site_ids": self.getSiteIds()},
                        context_instance=RequestContext(request))
        elif request.method == "POST":
            return self._handlePOST(request)


add_user = login_required(AddUserHandler())


class EditUserHandler(BaseUserHandler):
    def _getUser(self, user_name):
        connection = mongo_client.connection
        return connection["tjb-db"]["users"].find_one({"user_name": user_name})

    def editUser(self, user_name, password, is_admin, sites):
        update_dict = {"user_name": user_name, "is_admin": is_admin, "sites": sites}
        if password != "******":
            hashed_password, salt = createHashedPassword(password)
            update_dict["hashed_password"] = hashed_password
            update_dict["salt"] = salt
        connection = mongo_client.connection
        c_users = connection["tjb-db"]["users"]
        c_users.update({"user_name": user_name}, {"$set": update_dict})

    def _handlePOST(self, request):
        arguments = request.POST
        if not arguments.has_key("user_name") \
            or not arguments.has_key("password") \
            or not arguments.has_key("password_confirm") \
            or not arguments.has_key("is_admin"):
            return HttpResponse("EditUser: missing arguments")
        else:
            user_name =   arguments["user_name"]
            password = arguments["password"]
            password_confirm = arguments["password_confirm"]
            is_admin = arguments["is_admin"] == "true"
            site_ids = arguments.getlist("site_ids")

            if self._checkUserNameAvailable(user_name):
                return HttpResponse("User name does not exists.")
            elif password != "******" and not self._checkPasswordValid(password):
                return HttpResponse("Invalid password(length of password should be greater than 5 and only A-Z a-z 0-9 and underscore are permitted.)")
            elif not password == password_confirm:
                return HttpResponse("password and password(Confirm) do not match.")

            self.editUser(user_name, password, is_admin, site_ids)

            return HttpResponseRedirect("/edit_user?user_name=%s" % user_name)

    def _handleGET(self, request):
        user_name = request.GET["user_name"]
        if self._checkUserNameAvailable(user_name):
            return HttpResponse("user does not exist.")
        user = self._getUser(user_name)
        print "USER:", user
        return render_to_response("edit_user.html", 
                {"is_add_user": False, "data": user, "all_site_ids": self.getSiteIds()},
                context_instance=RequestContext(request))

    def __call__(self, request):
        if request.method == "GET":
            return self._handleGET(request)
        elif request.method == "POST":
            return self._handlePOST(request)


edit_user = login_required(EditUserHandler())

@login_required
def user_list(request):
    connection = mongo_client.connection
    user_list = [user for user in connection["tjb-db"]["users"].find()]
    return render_to_response("user_list.html",
                {"user_list": user_list})

@login_required
def ajax_load_site_checking_details(request):
    site_id = request.GET["site_id"]
    checking_id = request.GET["checking_id"]

    c_site_checking_daemon_logs = getSiteDBCollection(mongo_client.connection, site_id, "site_checking_daemon_logs")
    log = c_site_checking_daemon_logs.find_one({"checking_id": checking_id})
    
    log["formatted_created_on"] = log["created_on"].strftime("%Y-%m-%d %H:%M:%S")
    if log.has_key("ended_on"):
        log["formatted_ended_on"] = log["ended_on"].strftime("%Y-%m-%d %H:%M:%S")
    else:
        log["formatted_ended_on"] = "N/A"

    result = {"logs": log["logs"], "state": log["state"], "site_id": log["site_id"], "checking_id": log["checking_id"],
              "formatted_ended_on": log["formatted_ended_on"], "formatted_created_on": log["formatted_created_on"]}

    return HttpResponse(json.dumps(result))

@login_required
def site_checking_details(request):
    site_id = request.GET["site_id"]
    checking_id = request.GET["checking_id"]

    return render_to_response("site_checking_details.html",
                {"site_id": site_id, "checking_id": checking_id},
                context_instance=RequestContext(request))


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
    def addSite(self, site_id, site_name, calc_interval, disabledFlows, algorithm_type, available):
        connection = mongo_client.connection
        site = {"site_id": site_id,
                "last_update_ts": None,
                "disabledFlows": disabledFlows,
                "api_key": generateApiKey(connection, site_id, site_name),
                "site_name": site_name,
                "algorithm_type": algorithm_type,
                "calc_interval": calc_interval,
                "available": available}
        connection["tjb-db"]["sites"].save(site)

    def _checkSiteIdAvailable(self, site_id):
        connection = mongo_client.connection
        return connection["tjb-db"]["sites"].find_one({"site_id": site_id}) is None

    def _handlePOST(self, request):
        arguments = request.POST
        if not arguments.has_key("site_id") \
            or not arguments.has_key("site_name") \
            or not arguments.has_key("algorithm_type") \
            or not arguments.has_key("available") \
            or not arguments.has_key("calc_interval"):
            return HttpResponse("AddSite: missing arguments")
        else:
            site_id =   arguments["site_id"]
            site_name = arguments["site_name"]
            calc_interval = arguments["calc_interval"]
            disabledFlowsFormatted = arguments.get("disabledFlows", "")
            algorithm_type = arguments["algorithm_type"]
            available = arguments.get("available", '')

            if not self._checkSiteIdValid(site_id):
                return HttpResponse("site_id is not valid")
            elif not self._checkSiteIdAvailable(site_id):
                return HttpResponse("site_id already in use.")
            elif not self._checkCalcIntervalValid(calc_interval):
                return HttpResponse("calc_interval is not valid.")

            calc_interval = int(calc_interval)

            disabledFlows = self._parseDisabledFlows(disabledFlowsFormatted)
            self.addSite(site_id, site_name, calc_interval, disabledFlows, algorithm_type, available)

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
        connection = mongo_client.connection
        return connection["tjb-db"]["sites"].find_one({"site_id": site_id})

    def _updateSite(self, site_id, site_name, calc_interval, disabledFlows, algorithm_type, available):
        connection = mongo_client.connection
        site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
        site["site_name"] = site_name
        site["calc_interval"] = calc_interval
        site["disabledFlows"] = disabledFlows
        site["algorithm_type"] = algorithm_type
        site["available"] = available
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
            or not arguments.has_key("algorithm_type") \
            or not arguments.has_key("calc_interval"):
            return HttpResponse("EditSite: missing arguments")
        else:
            site_id =   arguments["site_id"]
            site_name = arguments["site_name"]
            calc_interval = arguments["calc_interval"]
            disabledFlowsFormatted = arguments.get("disabledFlowsFormatted", [""])
            algorithm_type = arguments["algorithm_type"]
            available = arguments.get("available", '')

            if not self._checkSiteIdValid(site_id):
                return HttpResponse("site_id is not valid")
            elif not self._checkCalcIntervalValid(calc_interval):
                return HttpResponse("calc_interval is not valid.")

            calc_interval = int(calc_interval)

            self._updateSite(site_id, site_name, calc_interval, 
                    self._parseDisabledFlows(disabledFlowsFormatted),
                    algorithm_type, available)

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

