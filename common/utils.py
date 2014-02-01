import datetime


def getSiteDBName(site_id):
    return "tjbsite_%s" % site_id


def getSiteDBCollection(connection, site_id, collection_name):
    return connection[getSiteDBName(site_id)][collection_name]


def getSiteDB(connection, site_id):
    return connection[getSiteDBName(site_id)]


def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def updateCategoryGroups(connection, site_id, category_groups_src):
    c_sites = connection["tjb-db"]["sites"]
    site = c_sites.find_one({"site_id": site_id})
    if site is not None:
        category_groups = {}
        for line in category_groups_src.split("\n"):
            line = line.strip()
            if line != "":
                splitted = line.strip().split(":")
                if len(splitted) != 2:
                    return False, "INVALID_FORMAT"
                else:
                    category_group, categories_str = splitted
                    categories_str = categories_str.strip()
                    if categories_str == "":
                        categories = []
                    else:
                        categories = categories_str.split(",")
                    for category in categories:
                        category_groups[category] = category_group
        c_sites.update({"site_id": site["site_id"]},
                {"$set": {"category_groups": category_groups,
                          "category_groups_src": category_groups_src}})
        return True, ""
    else:
        return False, "INVALID_SITE"


class UploadItemSimilarities:
    def __init__(self, connection, site_id, type="V"):
        self.connection = connection
        self.last_item1 = None
        self.last_rows = []
        self.item_similarities = getSiteDBCollection(self.connection, site_id,
                        "item_similarities_%s" % type)

#    def updateSimOneRow(self):
#        item_in_db = self.item_similarities.find_one({"item_id": self.last_item1})
#        if item_in_db is None:
#            item_in_db = {}
#        item_in_db.update({"item_id": self.last_item1, "mostSimilarItems": self.last_rows})
#        self.item_similarities.save(item_in_db)
#        self.last_item1 = self.item_id1
#        self.last_rows = []

    def updateSimOneRow(self):
        self.item_similarities.update({"item_id": self.last_item1},
                {"item_id": self.last_item1, "mostSimilarItems": self.last_rows}, upsert=True)
        self.last_item1 = self.item_id1
        self.last_rows = []

    def __call__(self, item_similarities_file_path):
        for line in open(item_similarities_file_path, "r"):
            self.item_id1, item_id2, similarity = line.split(",")
            similarity = float(similarity)
            if self.last_item1 is None:
                self.last_item1 = self.item_id1
            elif self.last_item1 != self.item_id1:
                self.updateSimOneRow()
            self.last_rows.append((item_id2, similarity))

        if len(self.last_rows) != 0:
            self.updateSimOneRow()


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


def convertTimedeltaAsDaysHoursMinutesSeconds(timedelta):
    if timedelta.days > 0:
        result_str = "%s days " % timedelta.days
    else:
        result_str = ""
    result_str += convertSecondsAsHoursMinutesSeconds(timedelta.seconds)
    return result_str


import urllib
import httplib
import re
import simplejson as json


class APIAccess:
    def __init__(self, server_name, server_port):
        self.server_name = server_name
        self.server_port = server_port

    def __call__(self, path, params, ptm_id=None, as_json=True, return_tuijianbaoid=False,
            assert_returns_tuijianbaoid=True, version="1.0", extra_headers={}):
        params_str = urllib.urlencode(params)
        headers = {}
        headers.update(extra_headers)
        if ptm_id != None:
            headers["Cookie"] = "__ptmid=%s" % ptm_id
        conn = httplib.HTTPConnection("%s:%s" % (self.server_name, self.server_port))
        conn.request("GET", "/%s" % version + path + "?" + params_str, headers=headers)
        response = conn.getresponse()
        result = response.read()
        response_cookie = response.getheader("set-cookie")
        if response_cookie is not None:
            response_tuijianbaoid = (re.match(r"__ptmid=([a-z0-9\-]+);", response_cookie).groups() or
                                        re.match(r"tuijianbaoid=([a-z0-9\-]+);", response_cookie).groups())[0]
        else:
            response_tuijianbaoid = None
        if assert_returns_tuijianbaoid and ptm_id is None:
            assert response_tuijianbaoid is not None, "response: %s" % result
        if as_json:
            try:
                result_obj = json.loads(result)
            except json.JSONDecodeError:
                raise Exception("Can't decode: %r" % result)
            body = result_obj
        else:
            body = result

        if return_tuijianbaoid:
            return body, response_tuijianbaoid
        else:
            return body


def smart_split(string, delimiter):
    string = string.strip()
    if string == "":
        return []
    else:
        return string.split(delimiter)


def trunc_list(list, max_size):
    if len(list) > max_size:
        return list[:max_size]
    else:
        return list


def getLatestUserOrderDatetime(connection, site_id):
    c_user_orders = getSiteDBCollection(connection, site_id, "user_orders")
    last_user_orders = [user_order for user_order in c_user_orders.find().sort("order_datetime", -1).limit(1)]
    if len(last_user_orders) == 0:
        latest_order_datetime = None
    else:
        latest_order_datetime = last_user_orders[0]["order_datetime"]
    return latest_order_datetime


def dt(dt_str):
    dt, _, us = dt_str.partition(".")
    dt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us = int(us.rstrip("Z"), 10)
    return dt + datetime.timedelta(microseconds=us)
