import sys
sys.path.insert(0, "../")
import hashlib
import datetime
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext
import pymongo
from common.utils import getSiteDBCollection

from ApiServer.mongo_client import MongoClient

import settings


def getConnection():
    return pymongo.Connection(settings.mongodb_host)

mongo_client = MongoClient(getConnection())


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
    return result


def login_required(callable):
    def method(request):
        if not request.session.has_key("user_name"):
            return redirect("/login")
        return callable(request)
    return method


@login_required
def index(request):
    user_name = request.session["user_name"]
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    c_sites = connection["tjb-db"]["sites"]
    user = c_users.find_one({"user_name": user_name})
    sites = [c_sites.find_one({"site_id": site_id}) for site_id in user["sites"]]
    for site in sites:
        site["items_count"] = getItemsAndCount(connection, site["site_id"])[1]
        site["statistics"] = getSiteStatistics(site["site_id"])
    return render_to_response("index.html", {"sites": sites, "user_name": user_name})


def getItemsAndCount(connection, site_id):
    c_items = getSiteDBCollection(connection, site_id, "items")
    items_cur = c_items.find({"available": True})
    items_count = items_cur.count()
    return items_cur, items_count


@login_required
def site_items_list(request):
    site_id = request.GET["site_id"]
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    items_cur, items_count = getItemsAndCount(connection, site_id)
    return render_to_response("site_items_list.html", 
            {"site": site, "items_count": items_count,
             "user_name": request.session["user_name"],
             "items": items_cur})

#from common.utils import APIAccess
#api_access = APIAccess(settings.api_server_name, settings.api_server_port)

@login_required
def show_item(request):
    site_id = request.GET["site_id"]
    item_id = request.GET["item_id"]
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    c_items = getSiteDBCollection(connection, site_id, "items")
    item_in_db = c_items.find_one({"item_id": item_id})
    topn = mongo_client.recommend_viewed_also_view(site_id, "V", item_id)
    def url_converter(url, site_id, item_id, req_id):
        return "/show_item?site_id=%s&item_id=%s" % (site_id, item_id)
    topn = mongo_client.convertTopNFormat(site_id, "null", topn, 15, url_converter=url_converter)
    for topn_item in topn:
        topn_item["score"] = float(topn_item["score"])
    return render_to_response("show_item.html",
        {"item": item_in_db, "user_name": request.session["user_name"], "getAlsoViewed": topn})


# Authentication System
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

