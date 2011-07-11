# coding=utf-8
import sys
sys.path.insert(0, "../")
import hashlib
import datetime
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext
import pymongo
from common.utils import getSiteDBCollection

import simplejson as json

from ApiServer.mongo_client import MongoClient

import settings


def getConnection():
    return pymongo.Connection(settings.mongodb_host)

mongo_client = MongoClient(getConnection())


def getSiteStatistics(site_id, days=14):
    c_statistics = getSiteDBCollection(getConnection(), site_id, "statistics")
    today_date = datetime.date.today()
    result = []
    for day_delta in range(days, -1, -1):
        the_date = today_date - datetime.timedelta(days=day_delta)
        the_date_str = the_date.strftime("%Y-%m-%d")
        row = c_statistics.find_one({"date": the_date_str})
        if row is None:
            row = {"date": the_date_str, "is_available": False}
        else:
            del row["_id"]
            row["is_available"] = True
            uv_v = float(row["UV_V"])
            pv_v = float(row["PV_V"])
            pv_uv = uv_v != 0.0 and (pv_v / uv_v) or 0
            row["PV_UV"] = "%.2f" % pv_uv
        result.append(row)
    return result


def login_required(callable):
    def method(request):
        if not request.session.has_key("user_name"):
            return redirect("/login")
        return callable(request)
    return method


def _getUserSites(user_name):
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    c_sites = connection["tjb-db"]["sites"]
    user = c_users.find_one({"user_name": user_name})
    sites = [c_sites.find_one({"site_id": site_id}) for site_id in user["sites"]]
    return sites


@login_required
def index(request):
    user_name = request.session["user_name"]
    sites = _getUserSites(user_name)
    return render_to_response("index.html", 
            {"page_name": "首页", "sites": sites, "user_name": user_name},
            context_instance=RequestContext(request))

@login_required
def ajax_get_site_statistics(request):
    connection = getConnection()
    user_name = request.session["user_name"]
    sites = _getUserSites(user_name)
    result = []
    for site in sites:
        site_id = site["site_id"]
        result.append({"site_id": site_id,
                       "items_count": getItemsAndCount(connection, site_id, 0)[1],
                       "statistics": getSiteStatistics(site_id)})
    return HttpResponse(json.dumps(result))



# TODO: let's use ranged query later.  as described here: http://stackoverflow.com/questions/5049992/mongodb-paging
# For now, we use skip + limit
PAGE_SIZE = 50
def getItemsAndCount(connection, site_id, page_num):
    c_items = getSiteDBCollection(connection, site_id, "items")
    items_cur = c_items.find({"available": True}).sort("item_name", 1)
    items_count = items_cur.count()
    items_cur.skip((page_num - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    return items_cur, items_count


@login_required
def site_items_list(request):
    site_id = request.GET["site_id"]
    page_num = int(request.GET.get("page_num", "1"))
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    items_cur, items_count = getItemsAndCount(connection, site_id, page_num)
    max_page_num = items_count / PAGE_SIZE
    if items_count % PAGE_SIZE > 0:
        max_page_num += 1
    return render_to_response("site_items_list.html", 
            {"page_name": u"%s商品列表" % site["site_name"],
             "site": site, "items_count": items_count,
             "user_name": request.session["user_name"],
             "items": items_cur,
             "page_num": page_num,
             "page_nums": xrange(1, max_page_num + 1)},
             context_instance=RequestContext(request))


import cgi
import urlparse
from common.utils import APIAccess
api_access = APIAccess(settings.api_server_name, settings.api_server_port)


def _getItemIdFromRedirectUrl(redirect_url):
    parsed_qs = cgi.parse_qs(urlparse.urlparse(redirect_url).query)
    item_id = parsed_qs["item_id"][0]
    return item_id


def _getTopnByAPI(site, path, item_id, amount):
    result = api_access("/%s" % path,
               {"api_key": site["api_key"],
                "item_id": item_id,
                "user_id": "null",
                "amount": amount,
                "not_log_action": "yes",
                "include_item_info": "yes"}
               )
    if result["code"] == 0:
        topn = result["topn"]
        for topn_item in topn:
            topn_item["item_link"] = "/show_item?site_id=%s&item_id=%s" % (site["site_id"], _getItemIdFromRedirectUrl(topn_item["item_link"]))
        return topn

def _getUltimatelyBought(site, item_id, amount):
    topn = _getTopnByAPI(site, "getUltimatelyBought", item_id, 15)
    for topn_item in topn:
        topn_item["score"] = "%.1f%%" % (topn_item["score"] * 100)
    return topn

@login_required
def show_item(request):
    site_id = request.GET["site_id"]
    item_id = request.GET["item_id"]
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    c_items = getSiteDBCollection(connection, site_id, "items")
    item_in_db = c_items.find_one({"item_id": item_id})
    return render_to_response("show_item.html",
        {"page_name": item_in_db["item_name"],
         "site": site,
         "item": item_in_db, "user_name": request.session["user_name"], 
         "getAlsoViewed": _getTopnByAPI(site, "getAlsoViewed", item_id, 15),
         "getAlsoBought": _getTopnByAPI(site, "getAlsoBought", item_id, 15),
         "getBoughtTogether": _getTopnByAPI(site, "getBoughtTogether", item_id, 15),
         "getUltimatelyBought": _getUltimatelyBought(site, item_id, 15)
         },
         context_instance=RequestContext(request))


def loadCategoryGroupsSrc(site_id):
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    return site.get("category_groups_src", "")

from common.utils import updateCategoryGroups
@login_required
def update_category_groups(request):
    if request.method == "GET":
        connection = getConnection()
        site_id = request.GET["site_id"]
        site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
        category_groups_src = loadCategoryGroupsSrc(site_id)
        return render_to_response("update_category_groups.html",
                {"site_id": site_id, "category_groups_src": category_groups_src,
                 "user_name": request.session["user_name"],
                 "page_name": u"编辑%s分类组别" % site["site_name"]},
                 context_instance=RequestContext(request))


#from django.views.decorators.csrf import csrf_exempt

@login_required
#@csrf_exempt
def ajax_update_category_groups(request):
    if request.method == "GET":
        site_id = request.GET["site_id"]
        category_groups_src = request.GET["category_groups_src"]
        connection = getConnection()
        is_succ, msg = updateCategoryGroups(connection, site_id, category_groups_src)
        result = {"is_succ": is_succ, "msg": msg}
        return HttpResponse(json.dumps(result))


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

