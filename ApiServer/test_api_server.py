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

from mongo_client import MongoClient

from common.utils import getSiteDBCollection
from common.utils import APIAccess


SERVER_NAME = "127.0.0.1"
SERVER_PORT = 15588

api_access = APIAccess(SERVER_NAME, SERVER_PORT)


def generate_uid():
    return hashlib.md5(repr(time.time())).hexdigest()


SITE_ID = "tester"

def getConnection():
    return pymongo.Connection(settings.mongodb_host)

mongo_client = MongoClient(getConnection())

def getApiKey(site_id):
    connection = pymongo.Connection(settings.mongodb_host)
    return connection["tjb-db"]["sites"].find_one({"site_id": site_id})["api_key"]

API_KEY = getApiKey(SITE_ID)


def uploadViewedUltimatelyBuys(records):
    c_viewed_ultimately_buys = getSiteDBCollection(getConnection(), SITE_ID, "viewed_ultimately_buys")
    for record in records:
        c_viewed_ultimately_buys.save(record)


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.connection = pymongo.Connection(settings.mongodb_host)
        self.cleanUpRawLogs()

    def tearDown(self):
        self.cleanUpItems()

    def updateItem(self, item_id, categories=""):
        import copy
        the_item = copy.copy(items_for_test.items[item_id])
        the_item["categories"] = categories
        result = api_access("/updateItem", the_item,
                    assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})

    def removeItem(self, item_id):
        result = api_access("/removeItem", {"api_key": API_KEY, "item_id": item_id},
                    assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})

    def cleanUpItems(self):
        getSiteDBCollection(self.connection, SITE_ID, "items").drop()

    def cleanUpViewedUltimatelyBuys(self):
        getSiteDBCollection(getConnection(), SITE_ID, "viewed_ultimately_buys").drop()

    def cleanUpBlackList(self):
        getSiteDBCollection(self.connection, SITE_ID, "rec_black_lists").drop()

    def updateCategoryGroups(self, category_groups_src):
        from common.utils import updateCategoryGroups
        updateCategoryGroups(self.connection, SITE_ID, category_groups_src)

    def cleanUpRawLogs(self):
        getSiteDBCollection(self.connection, SITE_ID, "raw_logs").drop()


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


class RefererRecordingTest(BaseTestCase):
    def test_viewItem1(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result, response_tuijianbaoid = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id},
            return_tuijianbaoid=True, extra_headers={"Referer": "http://blah"})
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(1)
        last_line = self.readLastLine()
        tjbid = last_line["tjbid"]
        self.assertEquals(tjbid, response_tuijianbaoid)
        self.assertSomeKeys(last_line, 
                {"behavior": "V", "user_id": user_id,
                 "referer": "http://blah",
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
             "referer": None,
             "tjbid": tjbid, "item_id": item_id})

class NotLogActionTest(BaseTestCase):
    def test(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result, response_tuijianbaoid = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id,
             "not_log_action": "yes"},
            return_tuijianbaoid=True, extra_headers={"Referer": "http://blah"})
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(0)



class ViewItemTest(BaseTestCase):
    def test_viewItem1(self):
        self.assertCurrentLinesCount(0)
        item_id, user_id = generate_uid(), generate_uid()
        result, response_tuijianbaoid = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id},
            return_tuijianbaoid=True, extra_headers={"Referer": "http://blah"})
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(1)
        last_line = self.readLastLine()
        tjbid = last_line["tjbid"]
        self.assertEquals(tjbid, response_tuijianbaoid)
        self.assertSomeKeys(last_line, 
                {"behavior": "V", "user_id": user_id,
                 "referer": "http://blah",
                 "item_id": item_id})
        
        item_id, user_id = generate_uid(), generate_uid()
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": item_id, "user_id": user_id},
            tuijianbaoid=tjbid,
            extra_headers={"Referer": "http://just"})
        self.assertEquals(result, {"code": 0})
        self.assertCurrentLinesCount(2)
        last_line = self.readLastLine()
        self.assertSomeKeys(last_line,
            {"behavior": "V", "user_id": user_id,
             "referer": "http://just",
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
        self.assertEquals(result, 'blah({"code": 2, "err_msg": "no such api_key"})')
        self.assertCurrentLinesCount(0)

    def test_user_id_item_id_validation(self):
        self.assertCurrentLinesCount(0)
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": "Ka KA", "user_id": "hi"},
            extra_headers={"Referer": "http://just"})
        self.assertEquals(result, {'code': 1, 'err_msg': 'invalid item_id or user_id'})
        self.assertCurrentLinesCount(1)
        last_line = self.readLastLine()
        self.assertSomeKeys(last_line,
        {"behavior": "ERROR"})
        self.assertSomeKeys(last_line["content"],
                {'item_id': 'Ka KA', 'user_id': 'hi', 
                 'referer': 'http://just', 
                 'behavior': 'V'})

        self.assertCurrentLinesCount(1)
        result = api_access("/viewItem",
            {"api_key": API_KEY, "item_id": "1", "user_id": "hey ya"},
            extra_headers={"Referer": "http://just1"})
        self.assertEquals(result, {'code': 1, 'err_msg': 'invalid item_id or user_id'})
        self.assertCurrentLinesCount(2)
        last_line = self.readLastLine()
        self.assertSomeKeys(last_line,
        {"behavior": "ERROR"})
        self.assertSomeKeys(last_line["content"],
                {'item_id': '1', 'user_id': 'hey ya', 
                 'referer': 'http://just1', 
                 'behavior': 'V'})



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


class UpdateCategoryTest(BaseTestCase):
    def cleanUpCategories(self):
        getSiteDBCollection(self.connection, SITE_ID, "categories").drop()

    def setUp(self):
        BaseTestCase.setUp(self)
        self.cleanUpCategories()

    def test_with_packedRequest(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("UCat", {"category_id": "448", "category_link": "/cat/448",
                               "category_name": "Eight", "parent_categories": "3,5"})
        result, response_tuijianbaoid = api_access("/packedRequest", 
                        pr.getUrlArgs(API_KEY), return_tuijianbaoid=True)
        self.assertCurrentLinesCount(0)
        full_name = packed_request.ACTION_NAME2FULL_NAME["UCat"]
        self.assertEquals(result, {'code': 0, 'responses': {full_name: {'code': 0}}})
        self.assertEqual(getSiteDBCollection(self.connection, SITE_ID, "categories").find().count(), 1)
        self.assertSomeKeys(getSiteDBCollection(self.connection, SITE_ID, "categories").find_one(),
                {"category_id": "448", "parent_categories": ["3", "5"], "category_link": "/cat/448",
                 "category_name": "Eight"})


    def test_updateCategory(self):
        result = api_access("/updateCategory",
                {"api_key": API_KEY, "category_id": "445", "category_link": "/cat/445",
                 "category_name": "Five"},
                assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        self.assertEqual(getSiteDBCollection(self.connection, SITE_ID, "categories").find().count(), 1)
        self.assertSomeKeys(getSiteDBCollection(self.connection, SITE_ID, "categories").find_one(),
                {"category_id": "445", "parent_categories": [], "category_link": "/cat/445",
                 "category_name": "Five"})

        result = api_access("/updateCategory",
                {"api_key": API_KEY, "category_id": "446", "category_link": "/cat/446",
                 "category_name": "Six"},
                assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        self.assertEqual(getSiteDBCollection(self.connection, SITE_ID, "categories").find().count(), 2)
        result = api_access("/updateCategory",
                {"api_key": API_KEY, "category_id": "445", "category_link": "/cat/445",
                 "category_name": "Five1", "parent_categories": "1,2"},
                assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        self.assertEqual(getSiteDBCollection(self.connection, SITE_ID, "categories").find().count(), 2)
        self.assertSomeKeys(getSiteDBCollection(self.connection, SITE_ID, "categories").\
                find_one({"category_id": "445"}),
                {"category_id": "445", "parent_categories": ["1", "2"], "category_link": "/cat/445",
                 "category_name": "Five1"})



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
                 "item_name": "Harry Potter I",
                 "categories": []})

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
                 "price": "25.0",
                 "categories": []})

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
                 "item_name": "Harry Potter II",
                 "categories": []})

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
                 "price": "15.0",
                 "categories": []})


    def testDoNotUpdateRemovedItem(self):
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
                 "item_name": "Harry Potter I",
                 "categories": []})

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
                 "item_name": "Harry Potter I",
                 "categories": []})

        # update it again, it should not be updated, and re-enabled.
        result = api_access("/updateItem",
            {"api_key": API_KEY, "item_id": item_id, 
             "item_link": "http://example.com/item?id=%s" % item_id,
             "item_name": "Harry Potter 8"},
             assert_returns_tuijianbaoid=False)
        self.assertEquals(result, {"code": 0})
        item_in_db = mongo_client.getItem(SITE_ID, item_id)
        del item_in_db["_id"]
        self.assertEquals(item_in_db,
                {"available": False,
                 "item_id": item_id, 
                 "item_link": "http://example.com/item?id=%s" % item_id,
                 "item_name": "Harry Potter I",
                 "categories": []})


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
                 "item_name": "Harry Potter I",
                 "categories": []})

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
                 "item_name": "Harry Potter I",
                 "categories": []})


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

    def decodeAndValidateRedirectUrlsForEachTopn(self, result, req_id, API_KEY):
        for result_row in result:
            self.decodeAndValidateRedirectUrls(result_row["topn"], req_id, API_KEY)


class BlackListTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
        self.cleanUpBlackList()

    def tearDown(self):
        BaseRecommendationTest.tearDown(self)
        self.cleanUpBlackList()

    def testByAlsoViewed(self):
        # toggle black list
        mongo_client.toggle_black_list(SITE_ID, "1", "3", True)
        #
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "4",
                 "include_item_info": "no"})
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [
                 {'item_id': '2', 'score': 0.99329999999999996}, 
                 {'item_id': '8', 'score': 0.99209999999999998}, 
                 {'item_id': '11', 'score': 0.98880000000000001},
                 {'item_id': '15', 'score': 0.98709999999999998}]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "4"})


class GetUltimatelyBoughtTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
        self.cleanUpBlackList()

        self.cleanUpViewedUltimatelyBuys()
        uploadViewedUltimatelyBuys(
            [
            {"item_id": "1",
             "total_views": 20,
             "viewedUltimatelyBuys": [
                {"item_id": "3", "count": 10, "percentage": 0.5},
                {"item_id": "11", "count": 5, "percentage": 0.25},
                {"item_id": "15", "count": 3, "percentage": 0.15},
                {"item_id": "2",  "count": 2, "percentage": 0.1}
             ]
             }
            ]
        )

    def tearDown(self):
        BaseRecommendationTest.tearDown(self)
        self.cleanUpViewedUltimatelyBuys()
        self.cleanUpBlackList()

    def testWithBlackList(self):
        # toogle black list
        mongo_client.toggle_black_list(SITE_ID, "1", "11", True)

        result = api_access("/getUltimatelyBought", 
                {"api_key": API_KEY, "user_id": "hah", "item_id": "1", "amount": "3",
                 "include_item_info": "no"})
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [{'item_id': '3', 'percentage': 50, 'score': 0.5}, 
                      {'item_id': '15', 'percentage': 15, 'score': 0.15},
                      {'item_id': '2', 'percentage': 10, 'score': 0.1}]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVUB",
             "req_id": req_id,
             "user_id": "hah",
             "item_id": "1",
             "amount": "3"})

    def test(self):
        result = api_access("/getUltimatelyBought", 
                {"api_key": API_KEY, "user_id": "hah", "item_id": "1", "amount": "3",
                 "include_item_info": "no"})
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [{'item_id': '3', 'percentage': 50, 'score': 0.5}, 
                      {'item_id': '11', 'percentage': 25, 'score': 0.25}, 
                      {'item_id': '15', 'percentage': 15, 'score': 0.15}]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVUB",
             "req_id": req_id,
             "user_id": "hah",
             "item_id": "1",
             "amount": "3"})


class GetByAlsoViewedTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")

    def test_SomeItemUnavailable(self):
        self.removeItem("2")
        result = api_access("/getAlsoViewed", 
                            {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "4",
                    "include_item_info": "no"})
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [
                 {'item_id': '3', 'score': 0.99880000000000002},
                 {'item_id': '8', 'score': 0.99209999999999998},
                 {'item_id': '11', 'score': 0.98880000000000001},
                 {'item_id': '15', 'score': 0.98709999999999998}
                 ]})
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecVAV",
             "req_id": req_id,
             "user_id": "ha",
             "item_id": "1",
             "amount": "4"})

    def test_same_group_only(self):
        self.updateItem("1", "CAT1")
        self.updateItem("2", "CAT2")
        self.updateItem("3", "CAT1")
        self.updateItem("8", "CAT2")
        self.updateItem("11", "CAT3")
        self.updateCategoryGroups("books:CAT1,CAT2\n"
                    "adult:CAT3\n")

        # item 11 should not be recommended
        result = api_access("/getAlsoViewed", 
                {"api_key": API_KEY, "user_id": "ha", "item_id": "1", "amount": "4",
                 "include_item_info": "no"})
        self.assertSomeKeys(result,
            {"code": 0,
             "topn": [{'item_id': '3', 'score': 0.99880000000000002}, 
                 {'item_id': '2', 'score': 0.99329999999999996}, 
                 {'item_id': '8', 'score': 0.99209999999999998}, 
                 {'item_id': '15', 'score': 0.98709999999999998}]})


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


class GetByEachPurchasedItemTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
        self.updateItem("30")
        self.cleanUpPurchasingHistory()

    def testWithPackedRequestAndIncludeItemInfoOff(self):
        self.assertCurrentLinesCount(0)

        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "ha",
                 "order_content": "1,2.5,1|2,1.3,2|8,3.3,1"},
                 return_tuijianbaoid=True)

        pr = packed_request.PackedRequest()
        pr.addRequest("RecEPI", {"user_id": "ha", "rec_row_max_amount": "2", "amount_for_each_item": "2", "include_item_info": "no"})
        result = api_access("/packedRequest", pr.getUrlArgs(API_KEY))
        self.assertCurrentLinesCount(2)
        self.assertEquals(result["code"], 0)
        self.assertEquals(len(result["responses"].keys()), 1)
        self.assertEquals(result["responses"]["getByEachPurchasedItem"]["result"],
              [{'by_item': {"item_id": "1"}, 
                                'topn': [{'item_id': '11', 'score': 0.99980000000000002}, 
                                         {'item_id': '3', 'score': 0.99880000000000002}]}, 
               {'by_item': {"item_id": "8"}, 
                     'topn': [{'item_id': '30', 'score': 0.99209999999999998}]}])


    def test(self):
        self.assertPurchasingHistoryCount(0)
        result = api_access("/getByEachPurchasedItem", 
                {"api_key": API_KEY, "user_id": "ha",
                 "rec_row_max_amount": "3",
                 "amount_for_each_item": "2",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["result"], [])

        # Place an order
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "ha",
                 "order_content": "1,2.5,1|2,1.3,2|8,3.3,1"},
                 return_tuijianbaoid=True)

        result = api_access("/getByEachPurchasedItem", 
                {"api_key": API_KEY, "user_id": "ha",
                 "rec_row_max_amount": "2",
                 "amount_for_each_item": "2",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrlsForEachTopn(result["result"], req_id, API_KEY)
        self.assertEquals(result["result"],
                        [{'by_item': {"item_id": "1", "item_name": "Turk", "item_link": "http://example.com/item?id=1"}, 
                          'topn': [{'item_name': 'Meditation', 'item_id': '11', 'score': 0.99980000000000002, 'item_link': 'http://example.com/item?id=11'}, 
                                   {'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}]}, 
                        {'by_item': {"item_id": "8", 
                                    "item_link": "http://example.com/item?id=8", 
                                    "item_name": "Best Books"}, 
                         'topn': [{'item_name': 'Not Recommended by Item 1', 'item_id': '30', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=30'}]}])


class GetByEachBrowsedItemTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
        self.updateItem("17")
        self.updateItem("30")
        self.cleanUpBlackList()

    def tearDown(self):
        BaseRecommendationTest.tearDown(self)
        self.cleanUpBlackList()

    def testWithBlackList(self):
        # toggle black list
        mongo_client.toggle_black_list(SITE_ID, "1", "3", True)
        mongo_client.toggle_black_list(SITE_ID, "8", "30", True)

        self.assertCurrentLinesCount(0)
        result = api_access("/getByEachBrowsedItem", 
                {"api_key": API_KEY, "user_id": "hah",
                 "browsing_history": "1,2,8",
                 "rec_row_max_amount": "2",
                 "amount_for_each_item": "3",
                 "include_item_info": "yes"})
        self.assertCurrentLinesCount(1)
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrlsForEachTopn(result["result"], req_id, API_KEY)
        self.assertEquals(result["result"], 
                [{'by_item': {"item_id": "1", "item_name": "Turk", 
                               "item_link": "http://example.com/item?id=1"}, 
                  'topn': [
                            {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                            {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'},
                            {'item_name': 'Who am I', 'item_id': '17', 'score': 0.97209999999999996, 'item_link': 'http://example.com/item?id=17'}
                           ]
                }       ]
        )
        last_line = self.readLastLine()
        self.assert_(last_line.has_key("tjbid"))
        self.assert_(last_line.has_key("timestamp"))
        self.assertSomeKeys(last_line, 
                {"user_id": "hah",
                 "behavior": "RecEBI",
                 "referer": None,
                 "amount_for_each_item": 3,
                 "is_empty_result": False,
                 "browsing_history": ["1", "2", "8"]})


    def testWithPackedRequest(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RecBTG", {"user_id": "null", "item_id": "1", "include_item_info": "no", "amount": 2})
        pr.addRequest("RecEBI", {"user_id": "null", "browsing_history": "1,8", "include_item_info": "no", "rec_row_max_amount": "2", "amount_for_each_item": "3"})
        result = api_access("/packedRequest", pr.getUrlArgs(API_KEY))
        self.assertCurrentLinesCount(2)
        self.assertEquals(result["code"], 0)
        self.assertEquals(len(result["responses"].keys()), 2)
        self.assertEquals(result["responses"]["getBoughtTogether"]["topn"],
                    [{'item_id': '3', 'score': 0.99770000000000003}, 
                     {'item_id': '2', 'score': 0.99329999999999996}
                    ])
        self.assertEquals(result["responses"]["getByEachBrowsedItem"]["result"],
              [{'by_item': {"item_id": "1"}, 'topn': [
                            {'item_id': '11', 'score': 0.98880000000000001},
                            {'item_id': '15', 'score': 0.98710000000000001},
                            {'item_id': '17', 'score': 0.97209999999999996}
                            ]}, 
                {'by_item': {'item_id': '8'}, 'topn': [
                            {'item_id': '30', 'score': 0.96999999999999997}]}])

    def test(self):
        self.assertCurrentLinesCount(0)
        result = api_access("/getByEachBrowsedItem", 
                {"api_key": API_KEY, "user_id": "hah",
                 "browsing_history": "1,2,8",
                 "rec_row_max_amount": "2",
                 "amount_for_each_item": "3",
                 "include_item_info": "yes"})
        self.assertCurrentLinesCount(1)
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrlsForEachTopn(result["result"], req_id, API_KEY)
        self.assertEquals(result["result"], 
                [{'by_item': {"item_id": "1", "item_name": "Turk", 
                              "item_link": "http://example.com/item?id=1"}, 
                  'topn': [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'}, 
                            {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                            {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'}
                           ]
                },
                 {'by_item': {"item_id": "8", 
                                    "item_link": "http://example.com/item?id=8", 
                                    "item_name": "Best Books"}, 
                  'topn': [{'item_name': 'Who am I', 'item_id': '17', 'score': 0.97999999999999998, 'item_link': 'http://example.com/item?id=17'},
                          {'item_name': 'Not Recommended by Item 1', 
                            'item_id': '30', 
                            'score': 0.96999999999999997, 
                            'item_link': 'http://example.com/item?id=30'}
                           ]
                 }
                ]
        )
        last_line = self.readLastLine()
        self.assert_(last_line.has_key("tjbid"))
        self.assert_(last_line.has_key("timestamp"))
        self.assertSomeKeys(last_line, 
                {"user_id": "hah",
                 "behavior": "RecEBI",
                 "referer": None,
                 "amount_for_each_item": 3,
                 "is_empty_result": False,
                 "browsing_history": ["1", "2", "8"]})


class GetByBrowsingHistoryTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.cleanUpBlackList()
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")

    def tearDown(self):
        BaseRecommendationTest.tearDown(self)
        self.cleanUpBlackList()

    def test_WithBlackList(self):
        mongo_client.toggle_black_list(SITE_ID, "1", "3", True)

        result = api_access("/getByBrowsingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "browsing_history": "1,2",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
        self.assertEquals(result["topn"], 
                [
                 {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}, 
                 {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                 {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'}])
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecBOBH",
             "req_id": req_id,
             "user_id": "ha",
             "browsing_history": ["1", "2"],
             "amount": "3"})


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

        self.removeItem("3")

        result = api_access("/getByBrowsingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "browsing_history": "1,2",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
        self.assertEquals(result["topn"], 
                [ {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99209999999999998, 'item_link': 'http://example.com/item?id=8'}, 
                 {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'},
                 {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98709999999999998, 'item_link': 'http://example.com/item?id=15'}
                 ])


class GetByShoppingCartTest2(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("8")
        self.updateItem("21")
        self.updateItem("29")
        self.updateItem("30")
        self.updateItem("11")

    def test(self):
        # to test byShoppingCart combines buy together and plo similarities.
        result = api_access("/getByShoppingCart", 
                {"api_key": API_KEY, "user_id": "ha",
                "shopping_cart": "8",
                "amount": "5",
                "include_item_info": "no"})
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["topn"],
                            [{'item_id': '21', 'score': 0.99280000000000002}, 
                             {'item_id': '29', 'score': 0.98309999999999997}, 
                             {'item_id': '30', 'score': 0.97209999999999996}, 
                             {'item_id': '11', 'score': 0.96209999999999996}])


class GetByShoppingCartTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")

    def test_GetByShoppingCart(self):
        # let's buy item with id 11.
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "ha",
                 "order_content": "15,2.5,1"},
                 return_tuijianbaoid=True)


        result = api_access("/getByShoppingCart", 
                {"api_key": API_KEY, "user_id": "ha",
                 "shopping_cart": "1,2",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
        self.assertEquals(result["topn"], 
                [{'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99770000000000003, 'item_link': 'http://example.com/item?id=3'}, 
                 {'item_name': 'Best Books', 'item_id': '8', 'score': 0.99250000000000005, 'item_link': 'http://example.com/item?id=8'}, 
                 {'item_name': 'Meditation', 'item_id': '11', 'score': 0.98880000000000001, 'item_link': 'http://example.com/item?id=11'}])
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecSC",
             "req_id": req_id,
             "user_id": "ha",
             "shopping_cart": ["1", "2"],
             "amount": "3"})


class GetByPurchasingHistoryTest(BaseRecommendationTest):
    def setUp(self):
        BaseRecommendationTest.setUp(self)
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
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
                {'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'},
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.98209999999999997, 'item_link': 'http://example.com/item?id=8'}
                 ])
        req_id = result["req_id"]
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "RecPH",
             "req_id": req_id,
             "user_id": "ha",
             "amount": "3"})

        # let's buy item with id 11.
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "ha",
                 "order_content": "11,2.5,1"},
                 return_tuijianbaoid=True)

        # now, item(11) should not be in the result
        result = api_access("/getByPurchasingHistory", 
                {"api_key": API_KEY, "user_id": "ha",
                 "amount": "3",
                 "include_item_info": "yes"})
        self.assertEquals(result["code"], 0)
        req_id = result["req_id"]
        self.decodeAndValidateRedirectUrls(result["topn"], req_id, API_KEY)
        self.assertEquals(result["topn"], 
                [
                {'item_name': 'Harry Potter I', 'item_id': '3', 'score': 0.99880000000000002, 'item_link': 'http://example.com/item?id=3'},
                {'item_name': 'Best Books', 'item_id': '8', 'score': 0.98209999999999997, 'item_link': 'http://example.com/item?id=8'},
                {'item_name': 'SaaS Book', 'item_id': '15', 'score': 0.98009999999999997, 'item_link': 'http://example.com/item?id=15'}
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

    def test_placeOrderWithOrderId(self):
        self.assertPurchasingHistoryCount(0)
        result, response_tuijianbaoid = api_access("/placeOrder", 
                {"api_key": API_KEY, "user_id": "guagua",
                 "order_content": "3,2.5,1|5,1.3,2",
                 "order_id": "ORDER_ID"},
                 return_tuijianbaoid=True)
        self.assertEquals(result, {"code": 0})
        self.assertSomeKeys(self.readLastLine(),
            {"behavior": "PLO",
             "user_id": "guagua",
             "tjbid": response_tuijianbaoid,
             "order_content": [{"item_id": "3", "price": "2.5", "amount": "1"},
                               {"item_id": "5", "price": "1.3", "amount": "2"}
                               ],
             "order_id": "ORDER_ID"})
        self.assertPurchasingHistoryCount(1)
        self.assertSomeKeys(self.readLastLine("purchasing_history"), 
                {"purchasing_history": ['3', '5'],
                 "user_id": "guagua"})


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
                               ],
             "order_id": None
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
    def setUp(self):
        BaseTestCase.setUp(self)
        self.updateItem("1")
        self.updateItem("3")
        self.updateItem("2")
        self.updateItem("8")
        self.updateItem("11")
        self.updateItem("15")
        self.updateItem("17")
        self.updateItem("21")
        self.updateItem("29")

    def testRecordReferer(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RSC", {"user_id": "guagua", "item_id": "25"})
        pr.addRequest("V", {"user_id": "guaye", "item_id": "35"})
        url_args = pr.getUrlArgs(API_KEY)
        url_args["callback"] = "callback"
        result, response_tuijianbaoid = api_access("/packedRequest", 
                url_args, as_json=False, return_tuijianbaoid=True,
                extra_headers={"Referer": "http://joe"})

        self.assertCurrentLinesCount(2)
        # TODO: check logs, also "action"
        self.assertSomeKeys(self.readLineMatch({"behavior": "RSC"}),
                {'user_id': 'guagua', 'behavior': 'RSC', 'item_id': '25',
                 'referer': 'http://joe'})
        self.assertSomeKeys(self.readLineMatch({"behavior": "V"}),
                {'user_id': 'guaye', 'behavior': 'V', 'item_id': '35',
                 'referer': 'http://joe'})


    def testSeveralRecommendation(self):
        self.assertCurrentLinesCount(0)
        pr = packed_request.PackedRequest()
        pr.addRequest("RecBTG", {"user_id": "null", "item_id": "1", "include_item_info": "no", "amount": 3})
        pr.addRequest("RecVAV", {"user_id": "null", "item_id": "1", "include_item_info": "no", "amount": 5})
        result = api_access("/packedRequest", pr.getUrlArgs(API_KEY))
        self.assertCurrentLinesCount(2)
        self.assertEquals(result["code"], 0)
        self.assertEquals(result["responses"]["getBoughtTogether"]["topn"],
                [{'item_id': '3', 'score': 0.99770000000000003}, 
                 {'item_id': '2', 'score': 0.99329999999999996}, 
                 {'item_id': '8', 'score': 0.99250000000000005}])
        self.assertEquals(result["responses"]["getAlsoViewed"]["topn"],
                [{'item_id': '11', 'score': 0.98880000000000001},
                 {'item_id': '15', 'score': 0.98709999999999998},
                 {'item_id': '17', 'score': 0.97209999999999996}, 
                 {'item_id': '21', 'score': 0.95109999999999995}, 
                 {'item_id': '29', 'score': 0.94110000000000005}])

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
                 'item_link': 'http://example.com/item?id=35',
                 'categories': []})

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
        self.assertEquals(result, {"code": 2, "err_msg": "no such api_key"})

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


def suite():
    suite = unittest.TestSuite()
    #suite.addTest(GetByEachPurchasedItemTest('testWithPackedRequest'))
    suite.addTest(UpdateItemTest('test_updateItem'))
    return suite


if __name__ == "__main__":
    unittest.main()
    #unittest.TextTestRunner(verbosity=2).run(suite())
