import sys
sys.path.insert(0, "../")
import hashlib
import datetime
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext
import pymongo
from common.utils import getSiteDBCollection

import settings


def getConnection():
    return pymongo.Connection(settings.mongodb_host)


def getSiteStatistics(site_id, days=7):
    c_statistics = getSiteDBCollection(getConnection(), site_id, "statistics")
    today_date = datetime.date.today()
    result = []
    for day_delta in range(0, days):
        the_date = today_date - datetime.timedelta(days=day_delta)
        the_date_str = the_date.strftime("%Y-%m-%d")
        row = c_statistics.find_one({"date": the_date_str})
        if row is None:
            row = {"date": the_date_str, "is_available": False}
        else:
            row["is_available"] = True
        result.append(row)
    print result
    return result


def index(request):
    if not request.session.has_key("user_name"):
        return redirect("/login")
    user_name = request.session["user_name"]
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    c_sites = connection["tjb-db"]["sites"]
    user = c_users.find_one({"user_name": user_name})
    sites = [c_sites.find_one({"site_id": site_id}) for site_id in user["sites"]]
    for site in sites:
        site["statistics"] = getSiteStatistics(site["site_id"])
    return render_to_response("index.html", {"sites": sites, "user_name": user_name})


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
        users = conn["tjb-db"]["users"]
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
        return conn["tjb-db"]["users"].find_one({"user_name": request.session["user_name"]})
    else:
        return None

