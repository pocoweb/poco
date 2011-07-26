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


def updateCollectionRecord(collection, key_name, key_value, initial_dict, content_dict):
    record_in_db = collection.find_one({key_name: key_value})
    if record_in_db is None:
        record_in_db = initial_dict
    record_in_db.update(content_dict)
    collection.save(record_in_db)


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

    def updateSimOneRow(self):
        item_in_db = self.item_similarities.find_one({"item_id": self.last_item1})
        if item_in_db is None:
            item_in_db = {}
        item_in_db.update({"item_id": self.last_item1, "mostSimilarItems": self.last_rows})
        self.item_similarities.save(item_in_db)
        self.last_item1 = self.item_id1
        self.last_rows = []

    def __call__(self, item_similarities_file_path):
        for line in open(item_similarities_file_path, "r"):
            self.item_id1, item_id2, similarity = line.split(",")
            similarity = float(similarity)
            if self.last_item1 is None:
                self.last_item1 = self.item_id1
                last_rows = []
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


import urllib
import httplib
import re
import simplejson as json
class APIAccess:
    def __init__(self, server_name, server_port):
        self.server_name = server_name
        self.server_port = server_port

    def __call__(self, path, params, tuijianbaoid=None, as_json=True, return_tuijianbaoid=False, 
            assert_returns_tuijianbaoid=True, version="1.0", extra_headers={}):
        params_str = urllib.urlencode(params)
        headers = {}
        headers.update(extra_headers)
        if tuijianbaoid <> None:
            headers["Cookie"] = "tuijianbaoid=%s" % tuijianbaoid
        conn = httplib.HTTPConnection("%s:%s" % (self.server_name, self.server_port))
        conn.request("GET", "/%s" % version + path + "?" + params_str, headers=headers)
        response = conn.getresponse()
        result = response.read()
        response_cookie = response.getheader("set-cookie")
        if response_cookie is not None:
            response_tuijianbaoid = re.match(r"tuijianbaoid=([a-z0-9\-]+);", 
                                                response_cookie).groups()[0]
        else:
            response_tuijianbaoid = None
        if assert_returns_tuijianbaoid and tuijianbaoid is None:
            assert response_tuijianbaoid is not None, "response: %s" % result
        if as_json:
            result_obj = json.loads(result)
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
