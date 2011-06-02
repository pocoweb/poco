import unittest
import urllib
import urllib2
import cookielib
import os
import os.path
import settings
import simplejson as json
import hashlib
import time

import items_for_test


SERVER_NAME = "127.0.0.1"
SERVER_PORT = 15588


#def reset_opener():
#    cookie = cookielib.CookieJar()
#    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
#    urllib2.install_opener(opener)
    

def api_access(path, params, tuijianbaoid=None, as_json=True):
    url = "http://%s:%s%s?%s" % (SERVER_NAME, SERVER_PORT, path, 
                    urllib.urlencode(params))
    req = urllib2.Request(url)
    if tuijianbaoid <> None:
        req.add_header("Cookie", "tuijianbaoid=%s" % tuijianbaoid)
    result = urllib2.urlopen(req).read()
    if as_json:
        result_obj = json.loads(result)
        return result_obj
    else:
        return result


def generate_uid():
    return hashlib.md5(repr(time.time())).hexdigest()

LOG_DIRECTORY = "test_directory"

def getCurrentFilePath(site_id):
    return os.path.join(LOG_DIRECTORY, site_id, "current")


#def resetCurrentFile(site_id):
#    file_path = os.path.join(settings.log_directory, site_id, "current")
#    if os.path.isfile(file_path):
#        os.remove(file_path)


def readCurrentFileLines(site_id):
    return open(getCurrentFilePath(site_id), "r").readlines()


def getLastLineSplitted(site_id):
    lines = readCurrentFileLines(site_id)
    return lines[-1].strip().split(",")


SITE_ID = "tester"


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        api_access("/rotateLogs", {})
    
    def updateItem(self, item_id):
        result = api_access("/tui/updateItem", items_for_test.items[item_id])
        self.assertEquals(result, {"code": 0})

class ViewItemTest(BaseTestCase):
    def test_viewItem1(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id})
        self.assertEquals(result, {"code": 0})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 1)
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "V") 
        self.assertEquals(rec_splitted[2], user_id)
        tuijianbaoid = rec_splitted[3]
        self.assertEquals(rec_splitted[4], item_id)
        
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id},
            tuijianbaoid=tuijianbaoid)
        self.assertEquals(result, {"code": 0})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 2)
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "V") 
        self.assertEquals(rec_splitted[2], user_id)
        self.assertEquals(rec_splitted[3], tuijianbaoid)
        self.assertEquals(rec_splitted[4], item_id)

    def test_wrongArguments(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id})
        self.assertEquals(result, {"code": 1})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)

        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "user_id": user_id})
        self.assertEquals(result, {"code": 1})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)

    def test_viewItemWithCallback(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id, "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 0})")
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 1)
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "V") 
        self.assertEquals(rec_splitted[2], user_id)
        self.assertEquals(rec_splitted[4], item_id)

    def test_viewItemSiteIdNotExists(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": "THESITEWHICHNOTEXISTS", "item_id": item_id, "user_id": user_id, 
             "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 2})")
        # TODO: should assert no record appended.
        self.assertEquals(readCurrentFileLines(SITE_ID), [])


class FavoriteItemTest(BaseTestCase):
    def test_addFavorite(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/addFavorite",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id})
        self.assertEquals(result,{"code": 0})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 1)
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "AF") 
        self.assertEquals(rec_splitted[2], user_id)
        self.assertEquals(rec_splitted[4], item_id)

    def test_removeFavorite(self):
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/removeFavorite",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id})
        self.assertEquals(len(readCurrentFileLines(SITE_ID)), 1)
        self.assertEquals(result,{"code": 0})
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RF") 
        self.assertEquals(rec_splitted[2], user_id)
        self.assertEquals(rec_splitted[4], item_id)


class RateItemTest(BaseTestCase):
    def test_rateItem(self):
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/rateItem",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id, "score": "5"})
        self.assertEquals(result,{"code": 0})
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RI") 
        self.assertEquals(rec_splitted[2], user_id)
        self.assertEquals(rec_splitted[4], item_id)
        self.assertEquals(rec_splitted[5], "5")


import mongo_client

class UpdateItemTest(BaseTestCase):
    def test_updateItem(self):
        item_id = generate_uid()
        result = api_access("/tui/updateItem",
            {"site_id": SITE_ID, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I"})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})

        # update an already existed item
        result = api_access("/tui/updateItem",
            {"site_id": SITE_ID, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter II",
             "price": "25.0"})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter II",
                 "price": "25.0"})

        # update an already existed item again
        result = api_access("/tui/updateItem",
            {"site_id": SITE_ID, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter II"})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter II"})

    def testUpdateItemWithOptionalParams(self):
        item_id = generate_uid()
        result = api_access("/tui/updateItem",
            {"site_id": SITE_ID, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I",
             "price": "15.0"})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I",
                 "price": "15.0"})

class RemoveItemTest(BaseTestCase):
    def test_removeItem(self):
        item_id = generate_uid()
        result = api_access("/tui/updateItem",
            {"site_id": SITE_ID, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I"})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})

        # remove the existed item
        result = api_access("/tui/removeItem",
            {"site_id": SITE_ID, "item_id": item_id})
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": False,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})


class RecommendViewedAlsoViewItemTest(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")

    def test_recommendViewedAlsoView(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "ha", "item_id": "1", "amount": "4",
                 "include_item_info": "no"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], 
                [{'item_id': '3', 'score': 0.99880000000000002}, 
                 {'item_id': '2', 'score': 0.99329999999999996}, 
                 {'item_id': '8', 'score': 0.99209999999999998}, 
                 {'item_id': '11', 'score': 0.98880000000000001}])
        req_id = result["req_id"]
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RecVAV")
        self.assertEquals(rec_splitted[2], req_id)
        self.assertEquals(rec_splitted[3], "ha")
        self.assertEquals(rec_splitted[5], "1")
        self.assertEquals(rec_splitted[6], "4")

    def test_IncludeItemInfoDefaultToYes(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "ha", "item_id": "1", "amount": "3"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                {'item_name': 'Lord of Ring I', 'item_id': '2', 'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}
                ])
        req_id = result["req_id"]
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RecVAV")
        self.assertEquals(rec_splitted[2], req_id)
        self.assertEquals(rec_splitted[3], "ha")
        self.assertEquals(rec_splitted[5], "1")
        self.assertEquals(rec_splitted[6], "3") 

    def test_amount_param(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "hah", "item_id": "1", "amount": "5"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                {'item_name': 'Lord of Ring I', 'item_id': '2', 'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'},
                {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'}
                ])
        req_id = result["req_id"]
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RecVAV")
        self.assertEquals(rec_splitted[2], req_id)
        self.assertEquals(rec_splitted[3], "hah")
        self.assertEquals(rec_splitted[5], "1")
        self.assertEquals(rec_splitted[6], "5")

    def test_IncludeItemInfoYes(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "ha", "item_id": "1", "amount": "4",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                {'item_name': 'Lord of Ring I', 'item_id': '2', 'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}, 
                {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'}])
        req_id = result["req_id"]
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RecVAV")
        self.assertEquals(rec_splitted[2], req_id)
        self.assertEquals(rec_splitted[3], "ha")
        self.assertEquals(rec_splitted[5], "1")
        self.assertEquals(rec_splitted[6], "4")        


class RecommendBasedOnBrowsingHistoryTest(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")

    def test_RecommendBasedOnBrowsingHistory(self):
        result = api_access("/tui/basedOnBrowsingHistory", 
                {"site_id": "tester", "user_id": "ha",
                 "browsing_history": "1,2",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                 {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}, 
                 {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'}])
        req_id = result["req_id"]
        rec_splitted = getLastLineSplitted(SITE_ID)
        self.assertEquals(rec_splitted[1], "RecBOBH")
        self.assertEquals(rec_splitted[2], req_id)
        self.assertEquals(rec_splitted[3], "ha")
        self.assertEquals(rec_splitted[5], "3")
        self.assertEquals(rec_splitted[6], "1|2") 


if __name__ == "__main__":
    unittest.main()

