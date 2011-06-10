#!/usr/bin/env python

import sys
sys.path.insert(0, "../")
import tornado.ioloop
import tornado.web
import simplejson as json
import re
import time
import os
import os.path
import signal
import uuid
import settings
import getopt


import mongo_client


# jquery serialize()  http://api.jquery.com/serialize/
# http://stackoverflow.com/questions/5784400/un-jquery-param-in-server-side-python-gae
# http://www.tsangpo.net/2010/04/24/unserialize-param-in-python.html

# TODO: referer; 

class LogWriter:
    def __init__(self):
        self.count = 0
        self.last_timestamp = None

    def writeEntry(self, site_id, content):
        timestamp = time.time()
        if timestamp <> self.last_timestamp:
            self.count = 0
        else:
            self.count += 1
        self.last_timestamp = timestamp
        timestamp_plus_count = "%r+%s" % (timestamp, self.count)
        content["timestamp"] = timestamp_plus_count
        if settings.print_raw_log:
            print "RAW LOG: site_id: %s, %s" % (site_id, content)
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
        site_id = args.get("site_id", None)
        callback = args.get("callback", None)

        site_ids = mongo_client.getSiteIds()
        if site_id not in site_ids:
            response = {'code': 2}
        else:
            del args["site_id"]
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


class TjbIdEnabledHandler(APIHandler):
    def prepare(self):
        tornado.web.RequestHandler.prepare(self)
        self.tuijianbaoid = self.get_cookie("tuijianbaoid")
        if not self.tuijianbaoid:
            self.tuijianbaoid = str(uuid.uuid4())
            self.set_cookie("tuijianbaoid", self.tuijianbaoid, expires_days=109500)


class SingleRequestHandler(TjbIdEnabledHandler):
    processor_class = None
    def process(self, site_id, args):
        processor = self.processor_class()
        err_msg, args = processor.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            args["tuijianbaoid"] = self.tuijianbaoid
            return processor.process(site_id, args)


class PackedRequestHandler(TjbIdEnabledHandler):
    def parseRequests(self, args):
        try:
            result = json.loads(args["requests"])
        except json.decoder.JSONDecodeError:
            raise ArgumentError("failed to decode: %s" % (args["requests"], ))
        if type(result) != list:
            raise ArgumentError("expect a list of requests, but get %s" % (args["requests"], ))
        return result

    def redirectRequest(self, site_id, action_name, request):
        request["site_id"] = site_id
        request["tuijianbaoid"] = self.tuijianbaoid
        processor = getProcessor(action_name)
        err_msg, args = processor.processArgs(request)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            args["tuijianbaoid"] = self.tuijianbaoid
            return processor.process(site_id, request)

    def process(self, site_id, args):
        if not args.has_key("requests"):
            raise ArgumentError("missing 'requests' param")
        requests = self.parseRequests(args)
        response = {"code": 0, "request_responses": {}}
        for request in requests:
            if type(request) != dict or not request.has_key("action"):
                raise ArgumentError("invalid request format: %s" % (request, ))
            action_name = request["action"]
            del request["action"]
            response["request_responses"][action_name] = self.redirectRequest(site_id, action_name, request)
        return response


class ActionProcessor:
    action_name = None
    def logAction(self, site_id, action_content, tjb_id_required=True):
        assert self.action_name != None
        if tjb_id_required:
            assert action_content.has_key("tjbid")
        action_content["behavior"] = self.action_name
        logWriter.writeEntry(site_id,
            action_content)

    def processArgs(self, args):
        return self.ap.processArgs(args)

    def process(self, site_id, args):
        pass


class ViewItemProcessor(ActionProcessor):
    action_name = "V"
    ap = ArgumentProcessor(
         (("item_id", True),
         ("user_id", True) # if no user_id, pass in "null"
        )
    )

    def process(self, site_id, args):
        self.logAction(site_id,
                {"user_id": args["user_id"],
                 "tjbid": args["tuijianbaoid"],
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
    def process(self, site_id, args):
        self.logAction(site_id,
                        {"user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
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
    def process(self, site_id, args):
        self.logAction(site_id, 
                        {"user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
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
    def process(self, site_id, args):
        self.logAction(site_id, 
                        {"user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
                         "item_id": args["item_id"],
                         "score": args["score"]})
        return {"code": 0}


class RateItemHandler(SingleRequestHandler):
    processor_class = RateItemProcessor


# FIXME: check user_id, the user_id can't be null.


class AddShopCartProcessor(ActionProcessor):
    action_name = "ASC"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         ("item_id", True),
        )
    )
    def process(self, site_id, args):
        self.logAction(site_id,
                        {"user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
                         "item_id": args["item_id"]})
        return {"code": 0}

class AddShopCartHandler(SingleRequestHandler):
    processor_class = AddShopCartProcessor



class RemoveShopCartProcessor(ActionProcessor):
    action_name = "RSC"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         ("item_id", True),
        )
    )
    def process(self, site_id, args):
        self.logAction(site_id,
                        {"user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
                         "item_id": args["item_id"]})
        return {"code": 0}

class RemoveShopCartHandler(SingleRequestHandler):
    processor_class = RemoveShopCartProcessor


class PlaceOrderProcessor(ActionProcessor):
    action_name = "PLO"
    ap = ArgumentProcessor(
        (
         ("user_id", True),
         # order_content Format: item_id,price,amount|item_id,price,amount
         ("order_content", True), 
        )
    )

    def _convertOrderContent(self, order_content):
        result = []
        for row in order_content.split("|"):
            item_id, price, amount = row.split(",")
            result.append({"item_id": item_id, "price": price,
                           "amount": amount})
        return result

    def process(self, site_id, args):
        self.logAction(site_id,
                       {"user_id": args["user_id"], 
                        "tjbid": args["tuijianbaoid"],
                        "order_content": self._convertOrderContent(args["order_content"])})
        return {"code": 0}

class PlaceOrderHandler(SingleRequestHandler):
    processor_class = PlaceOrderProcessor


# FIXME: update/remove item should be called in a secure way.
class UpdateItemHandler(APIHandler):
    ap = ArgumentProcessor(
         (("item_id", True),
         ("item_link", True),
         ("item_name", True),
         ("description", False),
         ("image_link", False),
         ("price", False),
         ("categories", False)
        )
    )

    def process(self, site_id, args):
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
            if args["categories"] is None:
                del args["categories"]
            mongo_client.updateItem(site_id, args)
            return {"code": 0}


class RemoveItemHandler(APIHandler):
    ap = ArgumentProcessor(
         [("item_id", True)]
        )

    def process(self, site_id, args):
        err_msg, args = self.ap.processArgs(args)
        if err_msg:
            return {"code": 1, "err_msg": err_msg}
        else:
            mongo_client.removeItem(site_id, args["item_id"])
            return {"code": 0}


#class ClickRecItemHandler(tornado.web.RequestHandler):
#    ap = ArgumentProcessor(
#        (("site_id", True),
#         ("item_id", True),
#         ("user_id", True),
#         ("req_id", True),
#         ("req_page", False),
#         ("callback", False)
#        )
#    )


def generateReqId():
    return str(uuid.uuid4())


# recommendViewedAlsoView LogFormat: timestamp,RecVAV,user_id,tuijianbaoid,item_id,amount

class RecommendViewedAlsoViewProcessor(ActionProcessor):
    action_name = "RecVAV"
    ap = ArgumentProcessor(
         (("user_id", True),
         ("item_id", True),
         ("include_item_info", False), # no, not include; yes, include
         ("amount", True),
        )
    )

    def logRecommendationRequest(self, args, site_id, req_id):
        self.logAction(site_id,
                        {"req_id": req_id,
                         "user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
                         "item_id": args["item_id"],
                         "amount": args["amount"]})

    def process(self, site_id, args):
        topn = mongo_client.recommend_viewed_also_view(site_id, args["item_id"], 
                        int(args["amount"]))
        include_item_info = args["include_item_info"] == "yes" or args["include_item_info"] is None
        topn = mongo_client.convertTopNFormat(site_id, topn, include_item_info)
        #topn = mongo_client.getCachedVAV(args["site_id"], args["item_id"]) 
        #                #,int(args["amount"]))
        req_id = generateReqId()
        self.logRecommendationRequest(args, site_id, req_id)
        return {"code": 0, "topn": topn, "req_id": req_id}

class RecommendViewedAlsoViewHandler(SingleRequestHandler):
    processor_class = RecommendViewedAlsoViewProcessor


class RecommendBasedOnBrowsingHistoryProcessor(ActionProcessor):
    action_name = "RecBOBH"
    ap = ArgumentProcessor(
    (
     ("user_id", True),
     ("browsing_history", False),
     ("include_item_info", False), # no, not include; yes, include
     ("amount", True),
    ))

    def logRecommendationRequest(self, args, site_id, req_id):
        browsing_history = args["browsing_history"].split(",")
        self.logAction(site_id,
                        {"req_id": req_id,
                         "user_id": args["user_id"], 
                         "tjbid": args["tuijianbaoid"], 
                         "amount": args["amount"],
                         "browsing_history": browsing_history})

    def process(self, site_id, args):
        browsing_history = args["browsing_history"]
        if browsing_history == None:
            browsing_history = []
        else:
            browsing_history = browsing_history.split(",")
        try:
            amount = int(args["amount"])
        except ValueError:
            return {"code": 1}
        include_item_info = args["include_item_info"] == "yes" or args["include_item_info"] is None
        topn = mongo_client.recommend_based_on_browsing_history(site_id, browsing_history, amount)
        topn = mongo_client.convertTopNFormat(site_id, topn, include_item_info)
        req_id = generateReqId()
        self.logRecommendationRequest(args, site_id, req_id)
        return {"code": 0, "topn": topn, "req_id": req_id}

class RecommendBasedOnBrowsingHistoryHandler(SingleRequestHandler):
    processor_class = RecommendBasedOnBrowsingHistoryProcessor


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{"version": "Tuijianbao v1.0"}')

processor_registry = {}

def registerProcessors(processor_classes):
    global processor_registry
    for processor_class in processor_classes:
        processor_registry[processor_class.action_name] = processor_class()

def getProcessor(action_name):
    return processor_registry[action_name]

registerProcessors([
        ViewItemProcessor, AddFavoriteProcessor, RemoveFavoriteProcessor,
        RateItemProcessor,AddShopCartProcessor, RemoveShopCartProcessor,
        PlaceOrderProcessor, RecommendViewedAlsoViewProcessor,
        RecommendBasedOnBrowsingHistoryProcessor
        ])

handlers = [
    (r"/", MainHandler),
    (r"/tui/viewItem", ViewItemHandler),
    (r"/tui/addFavorite", AddFavoriteHandler),
    (r"/tui/removeFavorite", RemoveFavoriteHandler),
    (r"/tui/rateItem", RateItemHandler),
    (r"/tui/removeItem", RemoveItemHandler),
    (r"/tui/updateItem", UpdateItemHandler),
    (r"/tui/addShopCart", AddShopCartHandler),
    (r"/tui/removeShopCart", RemoveShopCartHandler),
    (r"/tui/placeOrder", PlaceOrderHandler),
    (r"/tui/viewedAlsoView", RecommendViewedAlsoViewHandler),
    (r"/tui/basedOnBrowsingHistory", RecommendBasedOnBrowsingHistoryHandler),
    (r"/tui/packedRequest", PackedRequestHandler)
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
    application = tornado.web.Application(handlers)
    application.listen(port, settings.server_name)
    print "Listen at %s:%s" % (settings.server_name, port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
