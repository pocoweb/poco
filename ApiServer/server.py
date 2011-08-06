#!/usr/bin/env python

import sys
sys.path.insert(0, "../")
import tornado.ioloop
import tornado.web
import pymongo
import simplejson as json
import copy
import re
import time
import os
import os.path
import signal
import uuid
import settings
import getopt
import urllib
import logging


from common.utils import smart_split

from mongo_client import MongoClient
from mongo_client import SimpleRecommendationResultFilter
from mongo_client import SameGroupRecommendationResultFilter


logging.basicConfig(format="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
                    level=logging.WARNING,
                    datefmt="%Y-%m-%d %I:%M:%S")


def getConnection():
    return pymongo.Connection(settings.mongodb_host)


mongo_client = MongoClient(getConnection())

mongo_client.reloadApiKey2SiteID()

# jquery serialize()  http://api.jquery.com/serialize/
# http://stackoverflow.com/questions/5784400/un-jquery-param-in-server-side-python-gae
# http://www.tsangpo.net/2010/04/24/unserialize-param-in-python.html

# TODO: referer; 
# TODO: when to reload site ids.

class LogWriter:
    def __init__(self):
        self.local_file = open(settings.local_raw_log_file, "a")

    def closeLocalLog(self):
        self.local_file.close()

    def writeLineToLocalLog(self, site_id, line):
        full_line = "%s:%s\n" % (site_id, line)
        self.local_file.write(full_line)
        self.local_file.flush()

    def writeToLocalLog(self, site_id, content):
        line = json.dumps(content)
        self.writeLineToLocalLog(site_id, line)

    def writeEntry(self, site_id, content):
        timestamp = time.time()
        content["timestamp"] = timestamp
        if settings.print_raw_log:
            print "RAW LOG: site_id: %s, %s" % (site_id, content)
        self.writeToLocalLog(site_id, content)
        mongo_client.writeLogToMongo(site_id, content)


def extractArguments(request):
    result = {}
    for key in request.arguments.keys():
        result[key] = request.arguments[key][0]
    return result

class ArgumentProcessor:
    def __init__(self, definitions):
        self.definitions = definitions

    def processArgs(self, args):
        err_msg = None
        result = {}
        for argument_name, is_required in self.definitions:
            if not args.has_key(argument_name):
                if is_required:
                    err_msg = "%s is required." % argument_name
                else:
                    result[argument_name] = None
            else:
                result[argument_name] = args[argument_name]

        return err_msg, result

class ArgumentError(Exception):
    pass


# TODO: how to update cookie expires
class APIHandler(tornado.web.RequestHandler):
    def get(self):
        args = extractArguments(self.request)
        api_key = args.get("api_key", None)
        callback = args.get("callback", None)

        api_key2site_id = mongo_client.getApiKey2SiteID()
        if not api_key2site_id.has_key(api_key):
            response = {'code': 2, 'err_msg': 'no such api_key'}
        else:
            site_id = api_key2site_id[api_key]
            del args["api_key"]
            if callback is not None:
                del args["callback"]
            try:
                response = self.process(site_id, args)
            except ArgumentError as e:
                response = {"code": 1, "err_msg": e.message}
        response_json = json.dumps(response)
        if callback != None:
            response_text = "%s(%s)" % (callback, response_json)
        else:
            response_text = response_json
        self.write(response_text)

    def process(self, site_id, args):
        pass


class TjbIdEnabledHandlerMixin:
    def prepare(self):
        tornado.web.RequestHandler.prepare(self)
        self.tuijianbaoid = self.get_cookie("tuijianbaoid")
        if not self.tuijianbaoid:
            self.tuijianbaoid = str(uuid.uuid4())
            self.set_cookie("tuijianbaoid", self.tuijianbaoid, expires_days=109500)


class SingleRequestHandler(TjbIdEnabledHandlerMixin, APIHandler):
    processor_class = None
    def process(self, site_id, args):
        not_log_action = args.has_key("not_log_action")
        processor = self.processor_class(not_log_action)
        err_msg, args = processor.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            args["tuijianbaoid"] = self.tuijianbaoid
            referer = self.request.headers.get('Referer')
            args["referer"] = referer
            return processor.process(site_id, args)



class ActionProcessor:
    action_name = None

    def __init__(self, not_log_action=False):
        self.not_log_action = not_log_action

    def logAction(self, site_id, args, action_content, tjb_id_required=True):
        if not self.not_log_action:
            assert self.action_name != None
            if tjb_id_required:
                assert args.has_key("tuijianbaoid")
                action_content["tjbid"] = args["tuijianbaoid"]
            action_content["referer"] = args.get("referer", None)
            action_content["behavior"] = self.action_name
            logWriter.writeEntry(site_id,
                action_content)

    def processArgs(self, args):
        return self.ap.processArgs(args)

    def _process(self, site_id, args):
        raise NotImplemented

    def process(self, site_id, args):
        try:
            logWriter.writeLineToLocalLog(site_id, "BEGIN_REQUEST")
            try:
                return self._process(site_id, args)
            except ArgumentError:
                raise
            except:
                logging.critical("An Error occurred while processing action: site_id=%s, args=%s" % (site_id, args), exc_info=True)
                logWriter.writeLineToLocalLog(site_id, "UNKNOWN_ERROR:action_name=%s:args=%s" % (self.action_name, json.dumps(args)))
                return {"code": 99}
        finally:
            logWriter.writeLineToLocalLog(site_id, "END_REQUEST")


import re
class ViewItemProcessor(ActionProcessor):
    action_name = "V"
    ap = ArgumentProcessor(
         (("item_id", True),
         ("user_id", True) # if no user_id, pass in "null"
        )
    )

    def _validateInput(self, site_id, args):
        if re.match("[0-9a-zA-Z_-]+$", args["item_id"]) is None \
            or re.match("[0-9a-zA-Z_-]+$", args["user_id"]) is None:
            logWriter.writeEntry(site_id, 
                {"behavior": "ERROR", 
                 "content": {"behavior": "V",
                  "user_id": args["user_id"],
                  "tjbid": args["tuijianbaoid"],
                  "item_id": args["item_id"],
                  "referer": args.get("referer", None)}
                })
            raise ArgumentError("invalid item_id or user_id")

    def _process(self, site_id, args):
        self._validateInput(site_id, args)
        self.logAction(site_id, args,
                {"user_id": args["user_id"],
                 "item_id": args["item_id"]})
        return {"code": 0}


class ViewItemHandler(SingleRequestHandler):
    processor_class = ViewItemProcessor


# addFavorite LogFormat: timestamp,AF,user_id,tuijianbaoid,item_id


class AddFavoriteProcessor(ActionProcessor):
    action_name = "AF"
    ap = ArgumentProcessor(
        (
         ("item_id", True),
         ("user_id", True),
        )
    )
    def _process(self, site_id, args):
        self.logAction(site_id, args,
                        {"user_id": args["user_id"], 
                         "item_id": args["item_id"]})
        return {"code": 0}

class AddFavoriteHandler(SingleRequestHandler):
    processor_class = AddFavoriteProcessor


class RemoveFavoriteProcessor(ActionProcessor):
    action_name = "RF"
    ap = ArgumentProcessor(
         (("item_id", True),
         ("user_id", True),
        )
    )
    def _process(self, site_id, args):
        self.logAction(site_id, args,
                        {"user_id": args["user_id"], 
                         "item_id": args["item_id"]})
        return {"code": 0}


class RemoveFavoriteHandler(SingleRequestHandler):
    processor_class = RemoveFavoriteProcessor


class RateItemProcessor(ActionProcessor):
    action_name = "RI"
    ap = ArgumentProcessor(
         (("item_id", True),
         ("score", True),
         ("user_id", True),
        )
    )
    def _process(self, site_id, args):
        self.logAction(site_id, args,
                        {"user_id": args["user_id"], 
                         "item_id": args["item_id"],
                         "score": args["score"]})
        return {"code": 0}


class RateItemHandler(SingleRequestHandler):
    processor_class = RateItemProcessor


# FIXME: check user_id, the user_id can't be null.


class AddOrderItemProcessor(ActionProcessor):
    action_name = "ASC"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         ("item_id", True),
        )
    )
    def _process(self, site_id, args):
        self.logAction(site_id, args,
                        {"user_id": args["user_id"], 
                         "item_id": args["item_id"]})
        return {"code": 0}

class AddOrderItemHandler(SingleRequestHandler):
    processor_class = AddOrderItemProcessor


class RemoveOrderItemProcessor(ActionProcessor):
    action_name = "RSC"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         ("item_id", True),
        )
    )

    def _process(self, site_id, args):
        self.logAction(site_id, args,
                        {"user_id": args["user_id"], 
                         "item_id": args["item_id"]})
        return {"code": 0}


class RemoveOrderItemHandler(SingleRequestHandler):
    processor_class = RemoveOrderItemProcessor


class PlaceOrderProcessor(ActionProcessor):
    action_name = "PLO"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         # order_content Format: item_id,price,amount|item_id,price,amount
         ("order_content", True), 
         ("order_id", False)
        )
    )

    def _convertOrderContent(self, order_content):
        result = []
        for row in order_content.split("|"):
            item_id, price, amount = row.split(",")
            price = price.strip()
            result.append({"item_id": item_id, "price": price,
                           "amount": amount})
        return result

    def _process(self, site_id, args):
        self.logAction(site_id, args,
                       {"user_id":  args["user_id"], 
                        "order_id": args["order_id"],
                        "order_content": self._convertOrderContent(args["order_content"])})
        mongo_client.updateUserPurchasingHistory(site_id=site_id, user_id=args["user_id"])
        return {"code": 0}

class PlaceOrderHandler(SingleRequestHandler):
    processor_class = PlaceOrderProcessor


class UpdateCategoryProcessor(ActionProcessor):
    action_name = "UCat"
    ap = ArgumentProcessor(
         (("category_id", True),
         ("category_link", False),
         ("category_name", True),
         ("parent_categories", False)
        )
    )


    def _process(self, site_id, args):
        err_msg, args = self.ap.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            if args["parent_categories"] is None:
                args["parent_categories"] = []
            else:
                args["parent_categories"] = smart_split(args["parent_categories"], ",")
        mongo_client.updateCategory(site_id, args)
        return {"code": 0}


class UpdateCategoryHandler(APIHandler):
    processor = UpdateCategoryProcessor()

    def process(self, site_id, args):
        return self.processor.process(site_id, args)



class UpdateItemProcessor(ActionProcessor):
    action_name = "UItem"
    ap = ArgumentProcessor(
         (("item_id", True),
         ("item_link", True),
         ("item_name", True),
         ("description", False),
         ("image_link", False),
         ("price", False),
         ("market_price", False),
         ("categories", False)
        )
    )

    def _process(self, site_id, args):
        err_msg, args = self.ap.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            if args["description"] is None:
                del args["description"]
            if args["image_link"] is None:
                del args["image_link"]
            if args["price"] is None:
                del args["price"]
            if args["market_price"] is None:
                del args["market_price"]
            if args["categories"] is None:
                args["categories"] = []
            else:
                args["categories"] = smart_split(args["categories"], ",")
            mongo_client.updateItem(site_id, args)
            return {"code": 0}



# FIXME: update/remove item should be called in a secure way.
class UpdateItemHandler(APIHandler):
    processor = UpdateItemProcessor()

    def process(self, site_id, args):
        return self.processor.process(site_id, args)


class RemoveItemProcessor(ActionProcessor):
    action_name = "RItem"
    ap = ArgumentProcessor(
         [("item_id", True)]
        )

    def _process(self, site_id, args):
        err_msg, args = self.ap.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            mongo_client.removeItem(site_id, args["item_id"])
            return {"code": 0}



class RemoveItemHandler(APIHandler):
    processor = RemoveItemProcessor()

    def process(self, site_id, args):
        return self.processor.process(site_id, args)



class BaseRecommendationProcessor(ActionProcessor):

    def generateReqId(self):
        return str(uuid.uuid4())

    def _extractRecommendedItems(self, topn):
        return [topn_row["item_id"] for topn_row in topn]

    def getRedirectUrlFor(self, url, site_id, item_id, req_id):
        api_key = mongo_client.getSiteID2ApiKey()[site_id]
        param_str = urllib.urlencode({"url": url, "api_key": api_key, "item_id": item_id,
                          "req_id": req_id})
        full_url = settings.api_server_prefix + "/1.0/redirect?" + param_str
        return full_url

    def getRecommendationResultFilter(self, site_id, args):
        raise NotImplemented

    def getExcludedRecommendationItems(self):
        return getattr(self, "excluded_recommendation_items", set([]))


class BaseByEachItemProcessor(BaseRecommendationProcessor):
    # args should have "user_id", "tuijianbaoid"
    def getRecommendationLog(self, args, req_id, recommended_items):
        return {"req_id": req_id,
                "user_id": args["user_id"], 
                "tjbid": args["tuijianbaoid"], 
                "is_empty_result": len(recommended_items) == 0,
                "amount_for_each_item": self.getAmountForEachItem(args)
                }


    def getRecommendationsForEachItem(site_id, args):
        raise NotImplemented


    def getRecommendationResultFilter(self, site_id, args):
        raise NotImplemented


    def getRecRowMaxAmount(self, args):
        try:
            rec_row_max_amount = int(args["rec_row_max_amount"])
        except ValueError:
            raise ArgumentError("rec_row_max_amount should be an integer.")
        return rec_row_max_amount


    def getAmountForEachItem(self, args):
        try:
            amount_for_each_item = int(args["amount_for_each_item"])
        except ValueError:
            raise ArgumentError("amount_for_each_item should be an integer.")
        return amount_for_each_item


    def _process(self, site_id, args):
        self.recommended_items = None
        include_item_info = args["include_item_info"] == "yes" or args["include_item_info"] is None
        req_id = self.generateReqId()
        result_filter = self.getRecommendationResultFilter(site_id, args)

        amount_for_each_item = self.getAmountForEachItem(args)
        recommended_items = []
        recommendations_for_each_item = []
        for recommendation_for_item in self.getRecommendationsForEachItem(site_id, args):
            if include_item_info:
                by_item = mongo_client.getItem(site_id, recommendation_for_item["item_id"])
                del by_item["_id"]
                del by_item["available"]
                del by_item["categories"]
                del recommendation_for_item["item_id"]
                recommendation_for_item["by_item"] = by_item
            else:
                recommendation_for_item["by_item"] = {"item_id": recommendation_for_item["item_id"]}
                del recommendation_for_item["item_id"]
            topn = recommendation_for_item["topn"]
            excluded_recommendation_items = self.getExcludedRecommendationItems() | set(recommended_items)
            topn = mongo_client.convertTopNFormat(site_id, req_id, result_filter, topn,
                        amount_for_each_item, include_item_info, url_converter=self.getRedirectUrlFor,
                        excluded_recommendation_items=excluded_recommendation_items)
            if len(topn) > 0:
                recommendation_for_item["topn"] = topn
                recommended_items += self._extractRecommendedItems(topn)
                recommendations_for_each_item.append(recommendation_for_item)
            if len(recommendations_for_each_item) >= self.getRecRowMaxAmount(args):
                break

        self.logAction(site_id, args, self.getRecommendationLog(args, req_id, recommended_items))
        self.recommended_items = recommended_items
        return {"code": 0, "result": recommendations_for_each_item, "req_id": req_id}



class BaseSimpleResultRecommendationProcessor(BaseRecommendationProcessor):
    # args should have "user_id", "tuijianbaoid"
    def getRecommendationLog(self, args, req_id, recommended_items):
        return {"req_id": req_id,
                "user_id": args["user_id"], 
                "tjbid": args["tuijianbaoid"], 
                "recommended_items": recommended_items,
                "is_empty_result": len(recommended_items) == 0,
                "amount": args["amount"]}

    def postprocessTopN(self, topn):
        return

    def getTopN(self, site_id, args):
        raise NotImplemented

    def _process(self, site_id, args):
        self.recommended_items = None
        include_item_info = args["include_item_info"] == "yes" or args["include_item_info"] is None
        try:
            amount = int(args["amount"])
        except ValueError:
            raise ArgumentError("amount should be an integer.")
        req_id = self.generateReqId()
        topn = self.getTopN(site_id, args)
        result_filter = self.getRecommendationResultFilter(site_id, args)
        topn = mongo_client.convertTopNFormat(site_id, req_id, result_filter, topn,
                    amount, include_item_info, url_converter=self.getRedirectUrlFor,
                    excluded_recommendation_items=self.getExcludedRecommendationItems())
        self.postprocessTopN(topn)
        recommended_items = self._extractRecommendedItems(topn)
        self.logAction(site_id, args, self.getRecommendationLog(args, req_id, recommended_items))
        self.recommended_items = recommended_items
        return {"code": 0, "topn": topn, "req_id": req_id}




class BaseSimilarityProcessor(BaseSimpleResultRecommendationProcessor):
    similarity_type = None

    ap = ArgumentProcessor(
         (("user_id", True),
         ("item_id", True),
         ("include_item_info", False), # no, not include; yes, include
         ("amount", True),
        )
    )

    def getRecommendationLog(self, args, req_id, recommended_items):
        log = BaseSimpleResultRecommendationProcessor.getRecommendationLog(self, args, req_id, recommended_items)
        log["item_id"] = args["item_id"]
        return log

    def getTopN(self, site_id, args):
        connection = getConnection()
        return mongo_client.getSimilaritiesForItem(site_id, self.similarity_type, args["item_id"])


class GetByEachPurchasedItemProcessor(BaseByEachItemProcessor):
    action_name = "RecEPI"
    ap = ArgumentProcessor(
    (("user_id", True),
     ("include_item_info", False), # no, not include; yes, include
     ("rec_row_max_amount", True),
     ("amount_for_each_item", True),
    ))

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()

    def getRecommendationsForEachItem(self, site_id, args):
        user_id = args["user_id"]
        return mongo_client.recommend_by_each_purchased_item(site_id, user_id)


class GetByEachPurchasedItemHandler(SingleRequestHandler):
    processor_class = GetByEachPurchasedItemProcessor


class GetByEachBrowsedItemProcessor(BaseByEachItemProcessor):
    action_name = "RecEBI"
    ap = ArgumentProcessor(
    (
     ("user_id", True),
     ("browsing_history", False),
     ("include_item_info", False), # no, not include; yes, include
     ("rec_row_max_amount", True),
     ("amount_for_each_item", True),
    ))

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()

    def getBrowsingHistory(self, args):
        browsing_history = args["browsing_history"]
        if browsing_history == None:
            browsing_history = []
        else:
            browsing_history = browsing_history.split(",")
        return browsing_history

    def getRecommendationLog(self, args, req_id, recommended_items):
        log = BaseByEachItemProcessor.getRecommendationLog(self, args, req_id, recommended_items)
        log["browsing_history"] = self.getBrowsingHistory(args)
        return log

    def getRecommendationsForEachItem(self, site_id, args):
        browsing_history = self.getBrowsingHistory(args)
        return mongo_client.recommend_by_each_item(site_id, "V", browsing_history)


class GetByEachBrowsedItemHandler(SingleRequestHandler):
    processor_class = GetByEachBrowsedItemProcessor



class GetAlsoViewedProcessor(BaseSimilarityProcessor):
    action_name = "RecVAV"
    similarity_type = "V"

    def getRecommendationResultFilter(self, site_id, args):
        return SameGroupRecommendationResultFilter(mongo_client, site_id, args["item_id"])


class GetAlsoViewedHandler(SingleRequestHandler):
    processor_class = GetAlsoViewedProcessor


class GetAlsoBoughtProcessor(BaseSimilarityProcessor):
    action_name = "RecBAB"
    similarity_type = "PLO"

    def getRecommendationResultFilter(self, site_id, args):
        return SameGroupRecommendationResultFilter(mongo_client, site_id, args["item_id"])


class GetAlsoBoughtHandler(SingleRequestHandler):
    processor_class = GetAlsoBoughtProcessor


class GetBoughtTogetherProcessor(BaseSimilarityProcessor):
    action_name = "RecBTG"
    similarity_type = "BuyTogether"

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()


class GetBoughtTogetherHandler(SingleRequestHandler):
    processor_class = GetBoughtTogetherProcessor


class GetUltimatelyBoughtProcessor(BaseSimpleResultRecommendationProcessor):
    action_name = "RecVUB"
    ap = ArgumentProcessor(
         (("user_id", True),
         ("item_id", True),
         ("include_item_info", False), # no, not include; yes, include
         ("amount", True),
        )
    )

    def getRecommendationResultFilter(self, site_id, args):
        return SameGroupRecommendationResultFilter(mongo_client, site_id, args["item_id"])

    def getRecommendationLog(self, args, req_id, recommended_items):
        log = BaseSimpleResultRecommendationProcessor.getRecommendationLog(self, args, req_id, recommended_items)
        log["item_id"] = args["item_id"]
        return log

    def getTopN(self, site_id, args):
        return mongo_client.getSimilaritiesForViewedUltimatelyBuy(site_id, args["item_id"])

    def postprocessTopN(self, topn):
        for topn_item in topn:
            topn_item["percentage"] = int(round(topn_item["score"] * 100))


class GetUltimatelyBoughtHandler(SingleRequestHandler):
    processor_class = GetUltimatelyBoughtProcessor


class GetByBrowsingHistoryProcessor(BaseSimpleResultRecommendationProcessor):
    action_name = "RecBOBH"
    ap = ArgumentProcessor(
    (
     ("user_id", True),
     ("browsing_history", False),
     ("include_item_info", False), # no, not include; yes, include
     ("amount", True),
    ))

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()

    def getRecommendationLog(self, args, req_id, recommended_items):
        log = BaseSimpleResultRecommendationProcessor.getRecommendationLog(self, args, req_id, recommended_items)
        browsing_history = args["browsing_history"]
        if browsing_history == None:
            browsing_history = []
        else:
            browsing_history = browsing_history.split(",")
        log["browsing_history"] = browsing_history
        return log

    def getTopN(self, site_id, args):
        browsing_history = args["browsing_history"]
        if browsing_history == None:
            browsing_history = []
        else:
            browsing_history = browsing_history.split(",")
        return mongo_client.recommend_based_on_some_items(site_id, "V", browsing_history)


class GetByBrowsingHistoryHandler(SingleRequestHandler):
    processor_class = GetByBrowsingHistoryProcessor


class GetByShoppingCartProcessor(BaseSimpleResultRecommendationProcessor):
    action_name = "RecSC"
    ap = ArgumentProcessor(
    (
     ("user_id", True),
     ("shopping_cart", False),
     ("include_item_info", False), # no, not include; yes, include
     ("amount", True),
    ))

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()

    def getRecommendationLog(self, args, req_id, recommended_items):
        log = BaseSimpleResultRecommendationProcessor.getRecommendationLog(self, args, req_id, recommended_items)
        log["shopping_cart"] = args["shopping_cart"].split(",")
        return log

    def getTopN(self, site_id, args):
        shopping_cart = args["shopping_cart"]
        if shopping_cart == None:
            shopping_cart = []
        else:
            shopping_cart = shopping_cart.split(",")

        return mongo_client.recommend_based_on_shopping_cart(site_id, args["user_id"], shopping_cart)


class GetByShoppingCartHandler(SingleRequestHandler):
    processor_class = GetByShoppingCartProcessor


class GetByPurchasingHistoryProcessor(BaseSimpleResultRecommendationProcessor):
    action_name = "RecPH"
    ap = ArgumentProcessor(
    (("user_id", True),
     ("include_item_info", False), # no, not include; yes, include
     ("amount", True),
    ))

    def getRecommendationResultFilter(self, site_id, args):
        return SimpleRecommendationResultFilter()

    def getTopN(self, site_id, args):
        user_id = args["user_id"]
        if user_id == "null":
            return []
        else:
            return mongo_client.recommend_based_on_purchasing_history(site_id, user_id)


class GetByPurchasingHistoryHandler(SingleRequestHandler):
    processor_class = GetByPurchasingHistoryProcessor


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{"version": "Tuijianbao v1.0"}')


class RecommendedItemRedirectHandler(TjbIdEnabledHandlerMixin, tornado.web.RequestHandler):
    def get(self):
        url = self.request.arguments.get("url", [None])[0]
        api_key = self.request.arguments.get("api_key", [None])[0]
        req_id = self.request.arguments.get("req_id", [None])[0]
        item_id = self.request.arguments.get("item_id", [None])[0]
        
        api_key2site_id = mongo_client.getApiKey2SiteID()
        if url is None or not api_key2site_id.has_key(api_key):
            # FIXME
            self.write("wrong url")
            return
        else:
            site_id = api_key2site_id[api_key]
            log_content = {"behavior": "ClickRec", "url": url, 
                           "req_id": req_id, "item_id": item_id, "site_id": site_id,
                           "tjbid": self.tuijianbaoid}
            logWriter.writeEntry(site_id, log_content)
            self.redirect(url)
            return


ACTION_NAME2PROCESSOR_CLASS = {}
def fillActionName2ProcessorClass():
    _g = globals()
    global ACTION_NAME2PROCESSOR_CLASS
    processor_classes = []
    for key in _g.keys():
        if type(_g[key]) == type(ActionProcessor) and issubclass(_g[key], ActionProcessor):
            processor_classes.append(_g[key])
    for processor_class in processor_classes:
        ACTION_NAME2PROCESSOR_CLASS[processor_class.action_name] = processor_class
fillActionName2ProcessorClass()


def getAbbrName2RelatedInfo(abbr_map):
    result = {}
    _g = globals()
    for request_type in abbr_map.keys():
        for attr_abbr in abbr_map[request_type].keys():
            processor_class = ACTION_NAME2PROCESSOR_CLASS[abbr_map[request_type]["action_name"]]
            result[request_type + attr_abbr] = (processor_class,
                                                abbr_map[request_type]["full_name"],
                                                request_type,
                                                abbr_map[request_type][attr_abbr])
    return result


import packed_request
ABBR_NAME2RELATED_INFO = getAbbrName2RelatedInfo(packed_request._abbr_map)

MASK2ACTION_NAME = packed_request.MASK2ACTION_NAME

ACTION_NAME2FULL_NAME = packed_request.ACTION_NAME2FULL_NAME


# 1. use the masks
# 2. shared params
# 3. overriding
class PackedRequestHandler(TjbIdEnabledHandlerMixin, APIHandler):
    @staticmethod
    def extractRequests(args):
        global ABBR_NAME2RELATED_INFO
        args = copy.copy(args)
        processor_class2request_info = {}
        shared_params = {}
        remain_args = {}

        if not args.has_key("-"):
            raise ArgumentError("missing '-' argument")

        try:
            mask_set = int(args["-"], 16)
            del args["-"]
        except ValueError:
            raise ArgumentError("invalid '-' argument")

        for key in args.keys():
            if key.startswith("_"):
                shared_params[key[1:]] = args[key]
            else:
                remain_args[key] = args[key]

        for mask in MASK2ACTION_NAME.keys():
            if mask & mask_set != 0:
                action_name = MASK2ACTION_NAME[mask]
                full_name = ACTION_NAME2FULL_NAME[action_name]
                processor_class = ACTION_NAME2PROCESSOR_CLASS[action_name]
                processor_class2request_info[processor_class] = {"full_name": full_name,
                                                "processor_class": processor_class,
                                                "args": copy.copy(shared_params)}

        for key in remain_args.keys():
            _processor, full_name, request_type, attr_name = ABBR_NAME2RELATED_INFO.get(key, (None, None, None, None))
            if _processor is None:
                raise ArgumentError("invalid param:%s" % key)
            else:
                if not processor_class2request_info.has_key(_processor):
                    raise ArgumentError("argument %s not covered by mask_set." % key)
                processor_class2request_info[_processor]["args"][attr_name] = args[key]

        result = []
        def moveRequestInfo2Result(processor_class):
            if processor_class2request_info.has_key(processor_class):
                result.append(processor_class2request_info[processor_class])
                del processor_class2request_info[processor_class]
        moveRequestInfo2Result(GetBoughtTogetherProcessor)
        moveRequestInfo2Result(GetAlsoBoughtProcessor)
        moveRequestInfo2Result(GetUltimatelyBoughtProcessor)
        moveRequestInfo2Result(GetAlsoViewedProcessor)
        for processor_class in processor_class2request_info.keys():
            result.append(processor_class2request_info[processor_class])
        return result

    def redirectRequest(self, site_id, referer, processor_class, request_args):
        request_args["site_id"] = site_id
        processor = processor_class()
        err_msg, processed_args = processor.processArgs(request_args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            processed_args["tuijianbaoid"] = self.tuijianbaoid
            processed_args["referer"] = referer
            processor.excluded_recommendation_items = self.excluded_recommendation_items
            result = processor.process(site_id, processed_args)
            if isinstance(processor, BaseRecommendationProcessor) \
                and processor.recommended_items is not None:
                self.excluded_recommendation_items |= set(processor.recommended_items)
            return result


    def process(self, site_id, args):
        self.excluded_recommendation_items = set([])
        requests = self.extractRequests(args)
        response = {"code": 0, "responses": {}}
        referer = self.request.headers.get('Referer')
        for request_info in requests:
            full_name = request_info["full_name"]
            request_args = request_info["args"]
            processor_class = request_info["processor_class"]
            response["responses"][full_name] = \
                self.redirectRequest(site_id, referer, processor_class, request_args)
        return response


handlers = [
    (r"/", MainHandler),
    (r"/1.0/viewItem", ViewItemHandler),
    (r"/1.0/addFavorite", AddFavoriteHandler),
    (r"/1.0/removeFavorite", RemoveFavoriteHandler),
    (r"/1.0/rateItem", RateItemHandler),
    (r"/1.0/removeItem", RemoveItemHandler),
    (r"/1.0/updateItem", UpdateItemHandler),
    (r"/1.0/updateCategory", UpdateCategoryHandler),
    (r"/1.0/addOrderItem", AddOrderItemHandler),
    (r"/1.0/removeOrderItem", RemoveOrderItemHandler),
    (r"/1.0/placeOrder", PlaceOrderHandler),
    (r"/1.0/getAlsoViewed", GetAlsoViewedHandler),
    (r"/1.0/getByBrowsingHistory", GetByBrowsingHistoryHandler),
    (r"/1.0/getAlsoBought", GetAlsoBoughtHandler),
    (r"/1.0/getBoughtTogether", GetBoughtTogetherHandler),
    (r"/1.0/getUltimatelyBought", GetUltimatelyBoughtHandler),
    (r"/1.0/getByPurchasingHistory", GetByPurchasingHistoryHandler),
    (r"/1.0/getByShoppingCart", GetByShoppingCartHandler),
    (r"/1.0/getByEachBrowsedItem", GetByEachBrowsedItemHandler),
    (r"/1.0/getByEachPurchasedItem", GetByEachPurchasedItemHandler),
    (r"/1.0/packedRequest", PackedRequestHandler),
    (r"/1.0/redirect", RecommendedItemRedirectHandler)
    ]


def main():
    opts, _ = getopt.getopt(sys.argv[1:], 'p:', ['port='])
    port = settings.server_port
    for o, p in opts:
        if o in ['-p', '--port']:
            try:
                port = int(p)
            except ValueError:
                print "port should be integer"
    global logWriter
    logWriter = LogWriter()
    try:
        application = tornado.web.Application(handlers)
        application.listen(port, settings.server_name)
        print "Listen at %s:%s" % (settings.server_name, port)
        tornado.ioloop.IOLoop.instance().start()
    finally:
        logWriter.closeLocalLog()


if __name__ == "__main__":
    main()
