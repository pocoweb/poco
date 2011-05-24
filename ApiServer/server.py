#!/usr/bin/env python

import tornado.ioloop
import tornado.web
import simplejson as json
import re
import time
import os.path

import settings
import hbase_client

from utils import doHash

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{"version": "Tuijianbao v1.0"}')


customers = ["demo1", "mbaobao", "suning", "sample"]

# TODO: check site_id; referer; 

class LogWriter:
    def __init__(self):
        self.filesMap = {}
        self.count = 0
        self.last_timestamp = None

    def getFile(self, site_id):
        if not self.filesMap.has_key(site_id):
            customer_log_dir = os.path.join(settings.log_directory, site_id)
            if not os.path.isdir(customer_log_dir):
                os.mkdir(customer_log_dir)
            self.filesMap[site_id] = open("%s/current" % customer_log_dir, "a")
        return self.filesMap[site_id]

    def writeViewAction(self, action, site_id, item_id, user_id, session_id):
        line = "%s,%s,%s,%s\n" % (action, item_id, user_id, session_id)
        self.writeEntry(site_id, line)

    def writeEntry(self, site_id, line):
        f = self.getFile(site_id)
        timestamp = time.time()
        if timestamp <> self.last_timestamp:
            self.count = 0
        else:
            self.count += 1
        self.last_timestamp = timestamp
        timestamp_plus_count = "%r+%s" % (timestamp, self.count)
        f.write("%s,%s" % (timestamp_plus_count, line))
        f.flush()
        # Also write user action to browsing_history table.
        #hbase_client.insertBrowsingHistory(site_id, session_id, item_id, timestamp)
        

logWriter = LogWriter()

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
    def the_method(self, args):
        if args["site_id"] not in customers:
            return {"code": 2}
        else:
            return m(self, args)
    return the_method


class ViewItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        if args["site_id"] not in customers:
            return {"code": 2}
        else:
            logWriter.writeViewAction("V", args["site_id"], args["item_id"], 
                            args["user_id"], args["session_id"])
            return {"code": 0}


class AddFavoriteHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )


class RemoveFavoriteHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )


class RateItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("score", True),
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )


# FIXME
class updateShopCartHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )


class PlaceOrderHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_ids", True), # use comma to separate items
         ("user_id", True),
         ("session_id", True),
         ("callback", False)
        )
    )


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
        if args["site_id"] not in customers:
            return {"code": 2}
        else:
            del args["callback"]
            hbase_client.updateItem(args["site_id"], args)
            return {"code": 0}


class RemoveItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("callback", False)
        )
    )

    def removeItem(self, args):
        hbase_client.removeItem(args["site_id"], args["item_id"])

    @api_method
    @check_site_id
    def get(self, args):
        if args["site_id"] not in customers:
            return {"code": 2}
        else:
            self.removeItem(args)
            return {"code": 0}


class ClickRecItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True),
         ("session_id", True),
         ("rec_id", True),
         ("rec_page", False),
         ("callback", False)
        )
    )


class RecommendViewedAlsoViewHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("amount", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        topn = hbase_client.recommend_viewed_also_view(args["site_id"], args["item_id"], int(args["amount"]))
        return {"code": 0, "topn": topn}


class RecommendBasedOnBrowsingHistoryHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", False),
         ("browsing_history", True),
         ("amount", True),
         ("callback", False)
        ))

    @api_method
    @check_site_id
    def get(self, args):
        site_id = args["site_id"]
        browsing_history = args["browsing_history"].split(",")
        try:
            amount = int(args["amount"])
        except ValueError:
            return {"code": 1}
        topn = hbase_client.recommend_based_on_browsing_history(site_id, browsing_history, amount)
        return {"code": 0, "topn": topn}


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/action/viewItem", ViewItemHandler),
    (r"/manage/removeItem", RemoveItemHandler),
    (r"/manage/updateItem", UpdateItemHandler),
    (r"/recommend/viewedAlsoView", RecommendViewedAlsoViewHandler),
    (r"/recommend/basedOnBrowsingHistory", RecommendBasedOnBrowsingHistoryHandler)
])

if __name__ == "__main__":
    application.listen(settings.server_port, settings.server_name)
    tornado.ioloop.IOLoop.instance().start()

