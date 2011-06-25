import sys
sys.path.insert(0, "../")

import unittest
import urllib
import urllib2
import httplib
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

import re
def api_access(path, params, tuijianbaoid=None, as_json=True, return_tuijianbaoid=False, 
            assert_returns_tuijianbaoid=True, version="1.0"):
    params_str = urllib.urlencode(params)
    headers = {}
    if tuijianbaoid <> None:
        headers["Cookie"] = "tuijianbaoid=%s" % tuijianbaoid
    conn = httplib.HTTPConnection("%s:%s" % (SERVER_NAME, SERVER_PORT))
    #print "GET", path, params_str, headers
    #if tuijianbaoid <> None:
    #    conn.putheader("Cookie", "tuijianbaoid=%s" % tuijianbaoid)
    conn.request("GET", "/%s" % version + path + "?" + params_str, headers=headers)
    response = conn.getresponse()
    result = response.read()
    response_cookie = response.getheader("set-cookie")
    if response_cookie is not None:
        response_tuijianbaoid = re.match(r"tuijianbaoid=([a-z0-9\-]+);", response_cookie).groups()[0]
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



def generate_uid():
    return hashlib.md5(repr(time.time())).hexdigest()


SITE_ID = "tester"

def getApiKey(site_id):
    connection = pymongo.Connection(settings.mongodb_host)
    return connection["tjb-db"]["sites"].find_one({"site_id": site_id})["api_key"]

API_KEY = getApiKey(SITE_ID)


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = pymongo.Connection(settings.mongodb_host)
        self.cleanUpRawLogs()

    def updateItem(self, item_id):
        result = api_access("/updateItem", items_for_test.items[item_id],
                    assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})

    def cleanUpRawLogs(self):
        getSiteDBCollection(self.connection, SITE_ID, "raw_logs").drop()
        raw_logs = getSiteDBCollection(self.connection, SITE_ID, "raw_logs")
        for doc in raw_logs.find():
            raw_logs.remove(doc)
        pass

    def readCollectionLines(self, collection_name):
        return [line for line in getSiteDBCollection(self.connection, SITE_ID, collection_name).find()]

    def readCurrentLines(self):
        return self.readCollectionLines("raw_logs")

    def readLineMatch(self, criteria):
        return getSiteDBCollection(self.connection, SITE_ID, "raw_logs").find_one(criteria)

    def readLastLine(self, collection_name="raw_logs"):
        lines = self.readCollectionLines(collection_name)
        if len(lines) > 0:
            return lines[-1]
        else:
            return None

    def assertCurrentLinesCount(self, count):
        self.assertEquals(len(self.readCurrentLines()), count)

    def assertSomeKeys(self, theDict, keyValuesToCheck):
        for key in keyValuesToCheck.keys():
            self.assertEquals(theDict[key], keyValuesToCheck[key])

    def cleanUpPurchasingHistory(self):
        c_purchasing_history = getSiteDBCollection(self.connection, SITE_ID, "purchasing_history")
        for doc in c_purchasing_history.find():
            c_purchasing_history.remove(doc)

    def assertPurchasingHistoryCount(self, count):
        self.assertEquals(len(self.readCollectionLines("purchasing_history")), count)



class ViewItemTest(BaseTestCase):
    def test_viewItem1(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result, response_tuijianbaoid = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id},
            return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(1)
        last_line = self.readLastLine()
        tjbid = last_line["tjbid"]
        self.assertEquals(tjbid, response_tuijianbaoid)
        self.assertSomeKeys(last_line, 
                {"behavior": "V", "user_id": user_id,
                 "item_id": item_id})
        
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id},
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
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id})
        self.assertSomeKeys(result, {"code": 1})
        self.assertCurrentLinesCount(0)

        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/viewItem",
            {"api_key": API_KEY, "user_id": user_id})
        self.assertSomeKeys(result, {"code": 1})
        self.assertCurrentLinesCount(0)

    def test_viewItemWithCallback(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id, "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 0})")
        self.assertCurrentLinesCount(1)
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "V", "user_id": user_id, "item_id": item_id})

    def test_viewItemApiKeyNotExists(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/viewItem",
            {"api_key": "THEAPIKEYWHICHNOTEXISTS", "item_id": item_id, "user_id": user_id, 
             "callback": "blah"},
             as_json=False)
        self.assertEquals(result, "blah({\"code\": 2})")
        self.assertCurrentLinesCount(0)


class FavoriteItemTest(BaseTestCase):
    def test_addFavorite(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/addFavorite",
            {"api_key": API_KEY, "user_id": user_id,
             "item_id": item_id})
        self.assertSomeKeys(result,{"code": 0})
        self.assertCurrentLinesCount(1)
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "AF", "user_id": user_id, "item_id": item_id})

    def test_removeFavorite(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/removeFavorite",
            {"api_key": API_KEY, "user_id": user_id,
             "item_id": item_id})
        self.assertCurrentLinesCount(1)
        self.assertEquals(result,{"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RF", "user_id": user_id, "item_id": item_id})



class RateItemTest(BaseTestCase):
    def test_rateItem(self):
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/rateItem",
            {"api_key": API_KEY, "user_id": user_id,
             "item_id": item_id, "score": "5"})
        self.assertEquals(result,{"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RI", "user_id": user_id, "item_id": item_id,
             "score": "5"})



import mongo_client

class UpdateItemTest(BaseTestCase):
    def test_updateItem(self):
        item_id = generate_uid()
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I"},
             assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})

        # update an already existed item
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter II",
             "price": "25.0"},
             assert_returns_tuijianbaoid=False)
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
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter II"},
             assert_returns_tuijianbaoid=False)
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
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I",
             "price": "15.0"},
             assert_returns_tuijianbaoid=False)
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
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter I"},
             assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": True,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})

        # remove the existed item
        result = api_access("/removeItem",
            {"api_key": API_KEY, "item_id": item_id},
            assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": False,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I"})


class BaseRecommendationTest(BaseTestCase):
    def decodeAndValidateRedirectUrls(self, topn, req_id, api_key):
        import cgi
        import urlparse
        for topn_row in topn:
            parsed_qs = cgi.parse_qs(urlparse.urlparse(topn_row["item_link"]).query)
            original_url = parsed_qs["url"][0]
            self.assertEquals(parsed_qs["req_id"][0], req_id)
            self.assertEquals(parsed_qs["api_key"][0], api_key)
            self.assertEquals(parsed_qs["item_id"][0], topn_row["item_id"])
            topn_row["item_link"] = original_url


class GetByAlsoViewedTest(BaseRecommendationTest):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")

    def test_recommendViewedAlsoView(self):
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "4",
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
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "3"})
        req_id = result["req_id"]

        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)

        self.assertSomeKeys(result,
                {"code": 0,
                 "topn": [
                 {'item_name': 'Harry Potter I', 'item_id': '3', 
                        'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                 {'item_name': 'Lord of Ring I', 'item_id': '2', 
                        'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                 {'item_name': 'Best Books', 'item_id': '8', 
                        'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}
                ]})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "3"})

    def test_amount_param(self):
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "hah", "item_id": "1", "amount": "5"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)

        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                {'item_name': 'Lord of Ring I', 'item_id': '2', 'score': 0.99329999999999996, 'item_link': 'http://example.com/item?id=2'}, 
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'},
                {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'}
                ])
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "hah",
             "item_id": "1",
             "amount": "5"})

    def test_ItemNotExists(self):
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "haha", "item_id": "NOTEXISTS", "amount": "4"})
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
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "4",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
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


class GetByBrowsingHistoryTest(BaseRecommendationTest):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")

    def test_RecommendBasedOnBrowsingHistory(self):
        result = api_access("/getByBrowsingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "browsing_history": "1,2",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
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


class GetByPurchasingHistoryTest(BaseRecommendationTest):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.cleanUpPurchasingHistory()

    def test_RecommendGetByPurchasingHistory(self):
        self.assertPurchasingHistoryCount(0)
        result = api_access("/getByPurchasingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "amount": "3",
                 "include_item_info": "yes"})  
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"], [])

        # Place some order
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "ha",
                 "order_content": "1,2.5,1|2,1.3,2"},
                 return_tuijianbaoid=True)

        # now, let's try to get some recommendations
        result = api_access("/getByPurchasingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
        self.assertEquals(result["topn"], 
                [
                 {'item_name': 'Meditation', 'item_id': '11', 'score': 0.99980000000000002, 'item_link': 'http://example.com/item?id=11'},
                {'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}
                 ])
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecPH",
             "req_id": req_id,
             "user_id": "ha",
             "amount": "3"})



class AddShopCartTest(BaseTestCase):
    def test(self):
        result = api_access("/addOrderItem", 
                {"api_key": API_KEY, "user_id": "ha",
                 "item_id": "5"})
        self.assertEquals(result, {"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "ASC",
             "user_id": "ha",
             "item_id": "5",
             "user_id": "ha"})


class RemoveShopCartTest(BaseTestCase):
    def test(self):
        result = api_access("/removeOrderItem", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "item_id": "50"})
        self.assertEquals(result, {"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RSC",
             "user_id": "guagua",
             "item_id": "50"})


class PlaceOrderTest(BaseTestCase):
    def setUp(self):
        BaseTestCase.setUp(self)
        self.cleanUpPurchasingHistory()

    def test_PlaceOrder(self):
        self.assertPurchasingHistoryCount(0)
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "order_content": "3,2.5,1|5,1.3,2"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "PLO",
             "user_id": "guagua",
             "tjbid": response_tuijianbaoid,
             "order_content": [{"item_id": "3", "price": "2.5", "amount": "1"},
                               {"item_id": "5", "price": "1.3", "amount": "2"}
                               ]
            })
        self.assertPurchasingHistoryCount(1)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['3', '5'],
                 "user_id": "guagua"})

    def test_PurchasingHistory(self):
        self.assertPurchasingHistoryCount(0)
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "order_content": "3,2.5,1|5,1.3,2"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertPurchasingHistoryCount(1)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['3', '5'],
                 "user_id": "guagua"})

        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "order_content": "4,2.5,1|7,1.3,2"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertPurchasingHistoryCount(1)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['4', '7', '3', '5'],
                 "user_id": "guagua"})

        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "order_content": "5,2.5,1|3,1.3,2"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertPurchasingHistoryCount(1)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['5', '3', '4', '7'],
                 "user_id": "guagua"})

        # let's use another user "jacob"
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "jacob",
                 "order_content": "5,2.5,1|3,1.3,2"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertPurchasingHistoryCount(2)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['5', '3'],
                 "user_id": "jacob"})





import packed_request
class PackedRequestTest(BaseTestCase):
    def testUpdateItem(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("UItem", {"item_id": "35", "item_link": "http://example.com/item?id=35", 
               "item_name": "Something"})
        result, response_tuijianbaoid = api_access("/packedRequest", 
                        pr.getUrlArgs(API_KEY), return_tuijianbaoid=True)
        self.assertCurrentLinesCount(0)
        full_name = packed_request.ACTION_NAME2FULL_NAME["UItem"]
        self.assertEquals(result, {'code': 0, 'responses': {full_name: {'code': 0}}})
        item_in_db = mongo_client.getItem(SITE_ID, "35")
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {'item_name': 'Something', 
                 'item_id': '35', 
                 'available': True, 
                 'item_link': 'http://example.com/item?id=35'})

    def testWithCallback(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V", {"user_id": "guaye", "item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)
        url_args["callback"] = "callback"
        result, response_tuijianbaoid = api_access("/packedRequest", 
                url_args, as_json=False, return_tuijianbaoid=True)
        self.assertEquals(result,
                'callback({"code": 0, "responses": {"removeOrderItem": {"code": 0}, "viewItem": {"code": 0}}})')
        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'guagua', 'behavior': 'RSC', 'item_id': '25'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'guaye', 'behavior': 'V', 'item_id': '35'})
        # TODO: check tuijianbaoid
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          self.readLineMatch({"behavior": "V"})["tjbid"])
        self.assertEquals(response_tuijianbaoid,
                    self.readLineMatch({"behavior": "V"})["tjbid"])

    def testWithoutCallbackWithTjbidGiven(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V",   {"user_id": "guaye", "item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)
        result = api_access("/packedRequest", url_args, tuijianbaoid="blahblah")
        self.assertEquals(result,
                    {"code": 0,
                     "responses": 
                        {"viewItem": {"code": 0},
                         "removeOrderItem": {"code": 0}}
                    })
        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'guagua', 'behavior': 'RSC', 'item_id': '25'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'guaye', 'behavior': 'V', 'item_id': '35'})
        # TODO: check tuijianbaoid
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          self.readLineMatch({"behavior": "V"})["tjbid"])
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          "blahblah")

    def testWithoutCallbackArgumentSiteIdError(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V",   {"user_id": "guaye", "item_id": "35"})
        url_args = pr.getUrlArgs("SITENOTEXIST")
        result = api_access("/packedRequest", url_args)
        self.assertEquals(result,
                    {"code": 2})

    def testSharedParams1(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addSharedParams("user_id", "jason")
        pr.addRequest("RSC", {"item_id": "25"})
        pr.addRequest("V",   {"item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)
        result = api_access("/packedRequest", url_args, tuijianbaoid="blahblah")
        self.assertEquals(result,
                    {"code": 0,
                     "responses": 
                        {"viewItem": {"code": 0},
                         "removeOrderItem": {"code": 0}}
                    })
        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'jason', 'behavior': 'RSC', 'item_id': '25'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'jason', 'behavior': 'V', 'item_id': '35'})
        # TODO: check tuijianbaoid
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          self.readLineMatch({"behavior": "V"})["tjbid"])
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          "blahblah")

    def testSharedParams2(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addSharedParams("user_id", "jason")
        pr.addSharedParams("item_id", "25")
        pr.addRequest("RSC", {})
        pr.addRequest("V",   {"item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)
        result = api_access("/packedRequest", url_args, tuijianbaoid="blahblah")
        self.assertEquals(result,
                    {"code": 0,
                     "responses": 
                        {"viewItem": {"code": 0},
                         "removeOrderItem": {"code": 0}}
                    })
        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'jason', 'behavior': 'RSC', 'item_id': '25'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'jason', 'behavior': 'V', 'item_id': '35'})
        # TODO: check tuijianbaoid
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          self.readLineMatch({"behavior": "V"})["tjbid"])
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          "blahblah")


    def testWithoutCallbackArgumentMissing(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V",   {"user_id": "guaye"})
        url_args = pr.getUrlArgs(API_KEY)
        result = api_access("/packedRequest", url_args)
        self.assertEquals(result,
                    {"code": 0,
                     "responses":
                      {"viewItem": {"code": 1, 'err_msg': 'item_id is required.'},
                       "removeOrderItem": {"code": 0}}
                      })

    def testWithoutCallbackWithoutTjbidGiven(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V",   {"user_id": "guaye", "item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)

        result = api_access("/packedRequest", url_args)
        self.assertEquals(result,
                    {"code": 0,
                     "responses": 
                        {"viewItem": {"code": 0},
                         "removeOrderItem": {"code": 0}}
                    })
        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'guagua', 'behavior': 'RSC', 'item_id': '25'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'guaye', 'behavior': 'V', 'item_id': '35'})
        # TODO: check tuijianbaoid
        self.assertEquals(self.readLineMatch({"behavior": "RSC"})["tjbid"],
                          self.readLineMatch({"behavior": "RSC"})["tjbid"])



if __name__ == "__main__":
    unittest.main()

