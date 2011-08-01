# coding=utf-8
import sys
sys.path.insert(0, "../")
import hashlib
import datetime
from django.http import HttpResponse
from django.http import HttpResponseNotFound
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


def getSiteStatistics(site_id, days=45):
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
            row["PV_UV"] = float("%.2f" % pv_uv)

            pv_plo = float(row["PV_PLO"])
            pv_plo_d_uv = uv_v != 0.0 and (pv_plo / uv_v) or 0
            row["PV_PLO_D_UV"] = float("%.2f" % pv_plo_d_uv)





        result.append(row)
    return result

def convertColumns(row, column_names):
    for column_name in column_names:
        convertColumn(row, column_name)

def convertColumn(row, column_name):
    if row.has_key(column_name) and row[column_name] is not None:
        row[column_name] = float("%.3f" % row[column_name])
    else:
        row[column_name] = None

def login_required(callable):
    def method(request):
        if not request.session.has_key("user_name"):
            return redirect("/login")
        return callable(request)
    return method


# handlers with this decorator will only be available for admin users
# other users (not logged in or normal user) will receive a 404 error.
def login_and_admin_only(callable):
    def method(request):
        if not request.session.has_key("user_name"):
            return HttpResponseNotFound()
        else:
            user_name = request.session["user_name"]
            user = getUser(user_name)
            if not user["is_admin"]:
                return HttpResponseNotFound()
        return callable(request)
    return method


def _getUserSites(user_name):
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    c_sites = connection["tjb-db"]["sites"]
    user = c_users.find_one({"user_name": user_name})
    sites = [c_sites.find_one({"site_id": site_id}) for site_id in user["sites"]]
    return sites

def _getUserSiteIds(user_name):
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    user = c_users.find_one({"user_name": user_name})
    return user["sites"]

def getUser(user_name):
    connection = getConnection()
    c_users = connection["tjb-db"]["users"]
    user = c_users.find_one({"user_name": user_name})
    return user

@login_required
def index(request):
    user_name = request.session["user_name"]
    sites = _getUserSites(user_name)
    return render_to_response("index.html", 
            {"page_name": "首页", "sites": sites, "user_name": user_name,
             "user": getUser(user_name)},
            context_instance=RequestContext(request))


#@login_and_admin_only
#def admin_charts(request):
#    user_name = request.session["user_name"]
#    sites = _getUserSites(user_name)
#    return render_to_response("admin_charts.html", 
#            {"page_name": "首页", "sites": sites, "user_name": user_name,
#             "user": getUser(user_name)},
#            context_instance=RequestContext(request))


def _calc_rec_deltas(row):
    if row["avg_order_total"] is not None and row["avg_order_total_no_rec"] is not None:
        row["avg_order_total_rec_delta"] = row["avg_order_total"] - row["avg_order_total_no_rec"]
    else:
        row["avg_order_total_rec_delta"] = None

    if row["total_sales"] is not None and row["total_sales_no_rec"] is not None:
        row["total_sales_rec_delta"] = row["total_sales"] - row["total_sales_no_rec"]
        row["total_sales_rec_delta_ratio"] = row["total_sales_rec_delta"] / row["total_sales"]
        convertColumn(row, "total_sales_rec_delta_ratio")
    else:
        row["total_sales_rec_delta"] = None
        row["total_sales_rec_delta_ratio"] = None

def _calc_clickrec_pv_ratio(row):
    if row["PV_V"] is not None and row["ClickRec"] is not None and row["PV_V"] != 0:
        row["clickrec_pv_ratio"] = float(row["ClickRec"]) / float(row["PV_V"])
        convertColumn(row, "clickrec_pv_ratio")
    else:
        row["clickrec_pv_ratio"] = None

def _prepareCharts(user, statistics):
    data = {"pv_v": [], "uv_v": [], "pv_uv": [],
            "pv_plo": [], "pv_plo_d_uv": [], "pv_rec": [], "clickrec": [],
            "avg_order_total": [], "total_sales": [],
            "avg_order_total_no_rec": [], "total_sales_no_rec": [],
            "avg_order_total_rec_delta": [], "total_sales_rec_delta": [],
            "avg_unique_sku": [], "avg_item_amount": [],

            "categories": []}
    def pushIntoData(stat_row, keys):
        for key in keys:
            convertColumn(stat_row, key)
            if stat_row["is_available"]:
                data.setdefault(key.lower(), []).append(stat_row[key])
            else:
                data.setdefault(key.lower(), []).append(None)
    for stat_row in statistics:
        pushIntoData(stat_row, ["PV_V", "UV_V", "PV_UV", "PV_PLO", "PV_PLO_D_UV"])
        pushIntoData(stat_row, ["PV_Rec", "ClickRec"])
        _calc_clickrec_pv_ratio(stat_row)
        pushIntoData(stat_row, ["clickrec_pv_ratio"])
        pushIntoData(stat_row, ["avg_order_total", "total_sales"])

        pushIntoData(stat_row, ["avg_order_total_no_rec", "total_sales_no_rec"])
        _calc_rec_deltas(stat_row)
        pushIntoData(stat_row, ["avg_order_total_rec_delta", "total_sales_rec_delta"])
        pushIntoData(stat_row, ["total_sales_rec_delta_ratio"])
        pushIntoData(stat_row, ["avg_unique_sku", "avg_item_amount"])
        pushIntoData(stat_row, 
                ["click_rec_show_ratio_recph", "recommendation_request_count_recph", "recommendation_show_count_recph", "click_rec_count_recph"])
        pushIntoData(stat_row, 
                ["click_rec_show_ratio_recvav", "recommendation_request_count_recvav", "recommendation_show_count_recvav", "click_rec_count_recvav"])
        pushIntoData(stat_row,
                ["click_rec_show_ratio_recbab", "recommendation_request_count_recbab", "recommendation_show_count_recbab", "click_rec_count_recbab"])
        pushIntoData(stat_row,
                ["click_rec_show_ratio_recbtg", "recommendation_request_count_recbtg", "recommendation_show_count_recbtg", "click_rec_count_recbtg"])
        pushIntoData(stat_row,
                ["click_rec_show_ratio_recvub", "recommendation_request_count_recvub", "recommendation_show_count_recvub", "click_rec_count_recvub"])
        pushIntoData(stat_row,
                ["click_rec_show_ratio_recbobh", "recommendation_request_count_recbobh", "recommendation_show_count_recbobh", "click_rec_count_recbobh"])
        pushIntoData(stat_row,
                ["click_rec_show_ratio_recsc", "recommendation_request_count_recsc", "recommendation_show_count_recsc", "click_rec_count_recsc"])
        
        #data["categories"].append(stat_row["date"][5:])
        data["categories"].append(stat_row["date"][-2:])
    return data


# FIXME: should use a better way to to access restriction
@login_required
def ajax_get_site_statistics(request):
    site_id = request.GET.get("site_id", None)
    user_name = request.session["user_name"]
    user_site_ids = _getUserSiteIds(user_name)
    user = getUser(user_name)
    if site_id in user_site_ids:
        result = {"code": 0}
        connection = getConnection()
        result["site"] = {"site_id": site_id,
                       "items_count": getItemsAndCount(connection, site_id, 0)["items_count"],
                       "statistics": _prepareCharts(user, getSiteStatistics(site_id))}
        return HttpResponse(json.dumps(result))
    else:
        return HttpResponse(json.dumps({"code": 1}))



# TODO: let's use ranged query later.  as described here: http://stackoverflow.com/questions/5049992/mongodb-paging
# For now, we use skip + limit
PAGE_SIZE = 50
def getItemsAndCount(connection, site_id, page_num):
    c_items = getSiteDBCollection(connection, site_id, "items")
    items_cur = c_items.find({"available": True}).sort("item_name", 1)
    items_count = items_cur.count()
    items_cur.skip((page_num - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    max_page_num = items_count / PAGE_SIZE
    if items_count % PAGE_SIZE > 0:
        max_page_num += 1
    page_num_left = max(page_num - 4, 1)
    page_num_right = min(max_page_num, page_num + (9 - (page_num - page_num_left)))
    return {"items": items_cur, "items_count": items_count,
            "page_nums": xrange(page_num_left, page_num_right + 1),
            "page_num": page_num, "prev_page_num": max(1, page_num - 1),
            "next_page_num": min(max_page_num, page_num + 1),
            "max_page_num": max_page_num,
            "curr_left_reached": page_num == 1,
            "curr_right_reached": page_num >= max_page_num}


@login_required
def site_items_list(request):
    site_id = request.GET["site_id"]
    page_num = int(request.GET.get("page_num", "1"))
    connection = getConnection()
    site = connection["tjb-db"]["sites"].find_one({"site_id": site_id})
    result = {"page_name": u"%s商品列表" % site["site_name"],
             "site": site, 
             "user_name": request.session["user_name"]}
    result.update(getItemsAndCount(connection, site_id, page_num))
    return render_to_response("site_items_list.html", 
            result,
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


@login_required
def ajax_toggle_black_list(request):
    if request.method == "GET":
        site_id = request.GET["site_id"]
        item_id1 = request.GET["item_id1"]
        item_id2 = request.GET["item_id2"]
        is_on = request.GET["is_on"] == "true"
        mongo_client.toggle_black_list(site_id, item_id1, item_id2, is_on)
        return HttpResponse(json.dumps({"code": 0}))


def itemInfoListFromItemIdList(site_id, item_id_list):
    c_items = getSiteDBCollection(getConnection(), site_id, "items")
    item_info_list = [item for item in c_items.find({"item_id": {"$in": item_id_list}},
                                  {"item_id": 1, "item_name": 1, "item_link": 1}
                                  )]
    for item_info in item_info_list:
        del item_info["_id"]
    return item_info_list


@login_required
def ajax_get_black_list(request):
    if request.method == "GET":
        site_id = request.GET["site_id"]
        item_id = request.GET["item_id"]
        black_list = itemInfoListFromItemIdList(site_id, 
                        mongo_client.get_black_list(site_id, item_id))
        result = {"code": 0, "black_list": black_list}
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

