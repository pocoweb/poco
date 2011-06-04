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


import mongo_client


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


class ArgumentExtractor:
    def __init__(self, definitions):
        self.definitions = definitions

    def extractArguments(self, request):
        result = {}
        for argument_name, is_required in self.definitions:
            if request.arguments.has_key(argument_name):
                result[argument_name] = request.arguments[argument_name][0]
            else:
                if is_required:
                    result = None
                    break
                else:
                    result[argument_name] = None
        return result


def api_method(m):
    def the_method(self):
        args = self.ae.extractArguments(self.request)
        if args is None:
            self.write('{"code": 1}')
        else:
            callback = args["callback"]
            response = m(self, args)
            response_json = json.dumps(response)
            if callback != None:
                response_text = "%s(%s)" % (callback, response_json)
            else:
                response_text = response_json
            self.write(response_text)
    return the_method


def check_site_id(m):
    site_ids = mongo_client.getSiteIds()
    def the_method(self, args):
        if args["site_id"] not in site_ids:
            return {"code": 2}
        else:
            return m(self, args)
    return the_method



# TODO: how to update cookie expires
class APIHandler(tornado.web.RequestHandler):
    def prepare(self):
        tornado.web.RequestHandler.prepare(self)
        self.tuijianbaoid = self.get_cookie("tuijianbaoid")
        if not self.tuijianbaoid:
            self.tuijianbaoid = str(uuid.uuid4())
            self.set_cookie("tuijianbaoid", self.tuijianbaoid, expires_days=30)


# viewItem LogFormat: timestamp,V,user_id,tuijianbaoid,item_id
class ViewItemHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True), # if no user_id, pass in "null"
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"],
                {"behavior": "V",
                 "user_id": args["user_id"],
                 "tjbid": self.tuijianbaoid,
                 "item_id": args["item_id"]})
        return {"code": 0}

# addFavorite LogFormat: timestamp,AF,user_id,tuijianbaoid,item_id
class AddFavoriteHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"],
                        {"behavior": "AF",
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"]})
        return {"code": 0}


# removeFavorite LogFormat: timestamp,RF,user_id,tuijianbaoid,item_id
class RemoveFavoriteHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"], 
                        {"behavior": "RF",
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"]})
        return {"code": 0}


#rateItem LogFormat: timestamp,RI,user_id,tuijianbaoid,item_id,score
class RateItemHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("score", True),
         ("user_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"], 
                        {"behavior": "RI",
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"],
                         "score": args["score"]})
        return {"code": 0}


# FIXME: check user_id, the user_id can't be null.
class addShopCartHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("item_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"],
                        {"behavior": "ASC",
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"]})
        return {"code": 0}


class removeShopCartHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("item_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry(args["site_id"],
                        {"behavior": "RSC",
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"]})
        return {"code": 0}


#class PlaceOrderHandler(APIHandler):
#    ae = ArgumentExtractor(
#        (("site_id", True),
#         ("user_id", True),
#         ("order_content", True), # use comma to separate items
#         ("callback", False)
#        )
#    )

#    @api_method
#    @check_site_id
#    def get(self, args):
#        if args["site_id"] not in customers:
#            return {"code": 2}
#        else:
#            logWriter.writeEntry("PO", args["site_id"],  
#                            args["user_id"], args["item_id"])
#            return {"code": 0}


# FIXME: update/remove item should be called in a secure way.
class UpdateItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("item_link", True),
         ("item_name", True),
         ("callback", False),
         ("description", False),
         ("image_link", False),
         ("price", False),
         ("categories", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        del args["callback"]
        site_id = args["site_id"]
        del args["site_id"]
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


class RemoveItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("callback", False)
        )
    )

    def removeItem(self, args):
        site_id = args["site_id"]
        del args["site_id"]
        mongo_client.removeItem(site_id, args["item_id"])

    @api_method
    @check_site_id
    def get(self, args):
        self.removeItem(args)
        return {"code": 0}


#class ClickRecItemHandler(tornado.web.RequestHandler):
#    ae = ArgumentExtractor(
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
class RecommendViewedAlsoViewHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("item_id", True),
         ("include_item_info", False), # no, not include; yes, include
         ("amount", True),
         ("callback", False)
        )
    )

    def logRecommendationRequest(self, args, req_id):
        logWriter.writeEntry(args["site_id"],
                        {"behavior": "RecVAV",
                         "req_id": req_id,
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "item_id": args["item_id"],
                         "amount": args["amount"]})

    @api_method
    @check_site_id
    def get(self, args):
        topn = mongo_client.recommend_viewed_also_view(args["site_id"], args["item_id"], 
                        int(args["amount"]))
        include_item_info = args["include_item_info"] == "yes" or args["include_item_info"] is None
        topn = mongo_client.convertTopNFormat(args["site_id"], topn, include_item_info)
        #topn = mongo_client.getCachedVAV(args["site_id"], args["item_id"]) 
        #                #,int(args["amount"]))
        req_id = generateReqId()
        self.logRecommendationRequest(args, req_id)
        return {"code": 0, "topn": topn, "req_id": req_id}


# basedOnBrowsingHistory LogFormat: timestamp,RecBOBH,user_id,tuijianbaoid,amount,browsing_history
class RecommendBasedOnBrowsingHistoryHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("browsing_history", False),
         ("include_item_info", False), # no, not include; yes, include
         ("amount", True),
         ("callback", False)
        ))

    def logRecommendationRequest(self, args, req_id):
        browsing_history = args["browsing_history"].split(",")
        logWriter.writeEntry(args["site_id"],
                        {"behavior": "RecBOBH",
                         "req_id": req_id,
                         "user_id": args["user_id"], 
                         "tjbid": self.tuijianbaoid, 
                         "amount": args["amount"],
                         "browsing_history": browsing_history})

    @api_method
    @check_site_id
    def get(self, args):
        site_id = args["site_id"]
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
        topn = mongo_client.convertTopNFormat(args["site_id"], topn, include_item_info)
        req_id = generateReqId()
        self.logRecommendationRequest(args, req_id)
        return {"code": 0, "topn": topn, "req_id": req_id}


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{"version": "Tuijianbao v1.0"}')


handlers = [
    (r"/", MainHandler),
    (r"/tui/viewItem", ViewItemHandler),
    (r"/tui/addFavorite", AddFavoriteHandler),
    (r"/tui/removeFavorite", RemoveFavoriteHandler),
    (r"/tui/rateItem", RateItemHandler),
    (r"/tui/removeItem", RemoveItemHandler),
    (r"/tui/updateItem", UpdateItemHandler),
    (r"/tui/viewedAlsoView", RecommendViewedAlsoViewHandler),
    (r"/tui/basedOnBrowsingHistory", RecommendBasedOnBrowsingHistoryHandler)
    ]

def main():
    global logWriter
    logWriter = LogWriter()
    application = tornado.web.Application(handlers)
    application.listen(settings.server_port, settings.server_name)
    print "Listen at %s:%s" % (settings.server_name, settings.server_port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
