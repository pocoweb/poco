from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.shortcuts import redirect

import sqlite3
import simplejson as json
import urllib
import os.path

import settings

def getConnection():
    return sqlite3.connect(settings.USER_DB_PATH)


def fetch_books(item_ids):
    if len(item_ids) == 0:
        return []
    print "OR".join([" id:%s "] * len(item_ids))
    format = ("OR".join([" id:%s "] * len(item_ids)))
    query_string = format % tuple(item_ids)
    response = solr_query(query_string, defType="lucene", start=0)
    docs = response["response"]["docs"]
    result = []
    for item_id in item_ids:
        for doc in docs:
            if doc["id"] == str(item_id):
                result.append(doc)
                break
    return result




def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def my_algorithm(current_user):
    pref_ids = [pref["id"] for pref in current_user["prefs"]]
    if len(pref_ids) > 10:
        pref_ids1 = pref_ids[-10:]
    else:
        pref_ids1 = pref_ids
    rec_map = {}
    for pref_id in pref_ids1:
        recommended_items = fetch_most_similar_item_ids(pref_id)
        for rec_item, score in recommended_items:
            if int(rec_item) not in pref_ids:
                rec_map.setdefault(rec_item, [0,0])
                rec_map[rec_item][0] += float(score)
                rec_map[rec_item][1] += 1
    rec_tuples = []
    for key in rec_map.keys():
        score_total, count = rec_map[key][0], rec_map[key][1]
        rec_tuples.append((key, score_total / count))
    rec_tuples.sort(lambda a,b: sign(b[1] - a[1]))
    return [int(rec_tuple[0]) for rec_tuple in rec_tuples][:8]


def api_access(path, params):
    url = settings.API_URL_PREFIX + "%s?%s" % (path, urllib.urlencode(params))
    print "API_ACCESS:", url
    result = json.loads(urllib.urlopen(url).read())
    return result

def fetch_recommendations(current_user, request):
    pref_ids = [pref["id"] for pref in current_user["prefs"]]
    browsing_history = ",".join(pref_ids)
    params = {"site_id": "demo1", 
              "browsing_history": browsing_history,
              "amount": 8}
    result = api_access("/tui/basedOnBrowsingHistory", params)
    recommended_items = result["topn"]
    result = fetch_books(recommended_items)
    return result


def fetch_most_similar_item_ids(item_id):
    params = {"site_id": "demo1", "item_id": item_id, "amount": 10}
    result = api_access("/tui/viewedAlsoView", params)
    recommended_items = result["topn"]
    return recommended_items


def fetch_most_similar_items(item_id):
    recommended_items = [int(row[0]) for row in fetch_most_similar_item_ids(item_id)]
    result = fetch_books(recommended_items)
    return result


def rate_item(current_user, item_id):
    new_prefs = []
    for pref in current_user["prefs"]:
        if pref["id"] <> item_id:
            new_prefs.append(pref)
    new_prefs.insert(0, {"id": item_id})
    if len(new_prefs) > 30:
        new_prefs = new_prefs[:30]

    conn = getConnection()
    cur = conn.cursor()
    cur.execute("UPDATE userdb SET prefs_json=? WHERE name=?",
        (json.dumps(new_prefs), current_user["name"]))
    conn.commit()


import re
def google_it(request):
    title = request.GET["title"]
    return redirect("http://www.google.com/#%s" % urllib.urlencode({"q": title}))


def item_details(request):
    if not request.session.has_key("user_name"):
        return redirect("/login")
    current_user = _getCurrentUser(request)
    id = request.GET["id"]
    items = fetch_books([int(id)])
    item = items[0]

    # report view of items
    api_access("/tui/viewItem", {"site_id": "demo1", "item_id": item["id"], "user_id": "null", "session_id": request.session.session_key})
    rate_item(current_user, item["id"])
    current_user = _getCurrentUser(request)
    recommendations = fetch_recommendations(current_user, request)
    #
    return render_to_response("item_details.html", 
                        {"item": item, 
                        "recommended_items": recommendations,
                        "mostSimilarItems": fetch_most_similar_items(item["id"])})


def clean_all_ratings(request):
    conn = getConnection()
    cur = conn.cursor()    
    cur.execute("UPDATE userdb SET prefs_json=? WHERE name=?",
         [json.dumps([]), 
          request.session["user_name"]])
    conn.commit()
    conn.close()
    return redirect("/")


def api_rate(request):
    current_user = _getCurrentUser(request)
    user_id = current_user["id"]
    item_id = int(request.GET["item_id"])
    rate_item(current_user, item_id)
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("UPDATE userdb SET prefs_json=? WHERE name=?",
         [json.dumps(current_user["prefs"]), request.session["user_name"]])
    conn.commit()
    conn.close()
    return HttpResponse(json.dumps({"status": "OK"}))


def index(request):
    if not request.session.has_key("user_name"):
        return redirect("/login")
    current_user = _getCurrentUser(request)
    pref_items = fetch_books([pref["id"] for pref in current_user["prefs"]])
    user_id = current_user["id"]
    recommendations = fetch_recommendations(current_user, request)
    result = {"recommended_items": recommendations, 
              "current_user": current_user,
              "pref_items": pref_items,
              }
    return render_to_response('index.html', result)


def logout(request):
    del request.session["user_name"]
    return redirect("/")

def login(request):
    if request.method == "GET":
        msg = request.GET.get("msg", None)
        return render_to_response("login.html", {"msg": msg})
    else:
        conn = getConnection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM userdb WHERE name=? AND password=?", [request.POST["name"], request.POST["password"]])
        if len(cur.fetchall()) > 0:
            request.session["user_name"] = request.POST["name"]
            return redirect("/")
        else:
            return redirect("/login?msg=login_failed")

def read_record(line):
    part1, categories_str = line.split(",,")
    splitted = part1.split("\";\"")
    splitted[0] = splitted[0][1:]
    splitted[-1] = splitted[-1][:-1]
    item_id, isbn, title, author, year, publisher, image_url_s, image_url_m, _ = splitted
    item_id = int(item_id)
    return {"id": item_id, "title": title, "image_url_s": image_url_s,
            "image_url_m": image_url_m,
            "author": author}


ROWS_PER_PAGE = 20
def solr_query(query_string, defType=None, start=0):
    params = {"wt": "json",
              "version": "2.2",
              "indent": "on",
              "fl": "*, score",
              "start": start,
              "rows": ROWS_PER_PAGE,
              "q": query_string}
    if defType is not None:
        params["defType"] = defType

    #print "DEBUG: %@",params

    # FIXME: handle the case when response return an error.
    url = "http://localhost:8983/solr/select/?%s" % urllib.urlencode(params)
    result = urllib.urlopen(url).read()
    return json.loads(result)


def search(request):
    if not request.session.has_key("user_name"):
        return redirect("/login")
    page = "page" in request.GET and request.GET["page"] or "0"
    page = int(page)
    q = request.GET.get("q", "")
    if q == "":
        result = []
    else:
        result = solr_query(q, defType="edismax", start=page)

    return render_to_response("search.html", 
            {"q": q, 
             "result": result,
             "prev": page - ROWS_PER_PAGE,
             "next": page + ROWS_PER_PAGE,
             "current_user": _getCurrentUser(request),
            })


import copy
def _getCurrentUser(request):
    conn = getConnection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, prefs_json FROM userdb WHERE name=?",
          [request.session["user_name"]])
    row = cur.fetchone()
    user = {"id": row[0], "name": row[1], "prefs": json.loads(row[2])}
    return copy.deepcopy(user)
