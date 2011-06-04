import sys
sys.path.insert(0, "../")

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

import pymongo

from common.utils import getSiteDBCollection


SERVER_NAME = "127.0.0.1"
SERVER_PORT = 15588


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


SITE_ID = "tester"


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = pymongo.Connection()
        self.cleanUpRawLogs()

    def updateItem(self, item_id):
        result = api_access("/tui/updateItem", items_for_test.items[item_id])
        self.assertEquals(result, {"code": 0})

    def cleanUpRawLogs(self):
        getSiteDBCollection(self.connection, SITE_ID, "raw_logs").drop()
        raw_logs = getSiteDBCollection(self.connection, SITE_ID, "raw_logs")
        for doc in raw_logs.find():
            raw_logs.remove(doc)
        pass

    def readCurrentLines(self):
        return [line for line in getSiteDBCollection(self.connection, SITE_ID, "raw_logs").find()]

    def readLastLine(self):
        lines = self.readCurrentLines()
        if len(lines) > 0:
            return lines[-1]
        else:
            return None

    def assertCurrentLinesCount(self, count):
        self.assertEquals(len(self.readCurrentLines()), count)

    def assertSomeKeys(self, theDict, keyValuesToCheck):
        for key in keyValuesToCheck.keys():
            self.assertEquals(theDict[key], keyValuesToCheck[key])


class ViewItemTest(BaseTestCase):
    def test_viewItem1(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id})
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(1)
        last_line = self.readLastLine()
        tjbid = last_line["tjbid"]
        self.assertSomeKeys(last_line, 
                {"behavior": "V", "user_id": user_id,
                 "item_id": item_id})
        
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id},
            tuijianbaoid=tjbid)
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(2)
        last_line = self.readLastLine()
        self.assertSomeKeys(last_line,
            {"behavior": "V", "user_id": user_id,
             "tjbid": tjbid, "item_id": item_id})

    def test_wrongArguments(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id})
        self.assertEquals(result, {"code": 1})
        self.assertCurrentLinesCount(0)

        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "user_id": user_id})
        self.assertEquals(result, {"code": 1})
        self.assertCurrentLinesCount(0)

    def test_viewItemWithCallback(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id, "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 0})")
        self.assertCurrentLinesCount(1)
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "V", "user_id": user_id, "item_id": item_id})

    def test_viewItemSiteIdNotExists(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/viewItem",
            {"site_id": "THESITEWHICHNOTEXISTS", "item_id": item_id, "user_id": user_id, 
             "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 2})")
        self.assertCurrentLinesCount(0)




class FavoriteItemTest(BaseTestCase):
    def test_addFavorite(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/addFavorite",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id})
        self.assertEquals(result,{"code": 0})
        self.assertCurrentLinesCount(1)
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "AF", "user_id": user_id, "item_id": item_id})

    def test_removeFavorite(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/removeFavorite",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id})
        self.assertCurrentLinesCount(1)
        self.assertEquals(result,{"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RF", "user_id": user_id, "item_id": item_id})


class RateItemTest(BaseTestCase):
    def test_rateItem(self):
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/tui/rateItem",
            {"site_id": SITE_ID, "user_id": user_id,
             "item_id": item_id, "score": "5"})
        self.assertEquals(result,{"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RI", "user_id": user_id, "item_id": item_id,
             "score": "5"})

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
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [{'item_id': '3', 'score': 0.99880000000000002}, 
                 {'item_id': '2', 'score': 0.99329999999999996}, 
                 {'item_id': '8', 'score': 0.99209999999999998}, 
                 {'item_id': '11', 'score': 0.98880000000000001}]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "4"})

    def test_IncludeItemInfoDefaultToYes(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "ha", "item_id": "1", "amount": "3"})
        self.assertSomeKeys(result,
                {"code": 0,
                 "topn": [{'item_name': 'Harry Potter I', 'item_id': '3', 
                        'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                {'item_name': 'Lord of Ring I', 'item_id': '2', 
                        'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                {'item_name': 'Best Books', 'item_id': '8', 
                        'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}
                ]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "3"})

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
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "hah",
             "item_id": "1",
             "amount": "5"})

    def test_ItemNotExists(self):
        result = api_access("/tui/viewedAlsoView", 
                {"site_id": "tester", "user_id": "haha", "item_id": "NOTEXISTS", "amount": "4"})
        self.assertSomeKeys(result,
                {"code": 0,
                 "topn": []})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "haha",
             "item_id": "NOTEXISTS",
             "amount": "4"})


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
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "4"})


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
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecBOBH",
             "req_id": req_id,
             "user_id": "ha",
             "browsing_history": ["1", "2"],
             "amount": "3"})


if __name__ == "__main__":
    unittest.main()
    sys.exit(0)

