#!/usr/bin/env python

import sys
sys.path.append("../pylib")
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

from utils import doHash
import utils


class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('{"version": "Tuijianbao v1.0"}')


# TODO: referer; 

class LogWriter:
    def __init__(self):
        self.filesMap = {}
        self.count = 0
        self.last_timestamp = None
        self.prepareLogDirAndFiles()
        if settings.rotation_interval != -1:
            self.startRotationLoop()

    def startRotationLoop(self):
        self.doRotateFiles()
        tornado.ioloop.IOLoop.instance().add_timeout(
                time.time() + settings.rotation_interval / 2, 
                self.startRotationLoop)

    def _generateDestFilePath(self, site_id):
        ts = time.time()
        while True:
            dest_file_name = repr(ts)
            dest_file_path = utils.getLogFilePath(site_id, dest_file_name)
            if not os.path.exists(dest_file_path):
                break
            ts += 0.001
        return dest_file_path

    def doRotateFiles(self):
        # TODO: need a more scalable solution
        for site_id in mongo_client.getSiteIds():
            current_file_path = utils.getLogFilePath(site_id, "current")
            # Do not rotate a 0 size "current" file.
            last_rotation_ts = self.loadLastRotationTS(site_id)
            if os.stat(current_file_path).st_size <> 0 \
                and (time.time() - last_rotation_ts > settings.rotation_interval):
                print "Start to Rotate ... "
                self.filesMap[site_id].close()
                dest_file_path = self._generateDestFilePath(site_id)
                # this marks that we are 
                # not sure if "mv" is atomic, if the new_path does not exist.
                # according to "However, when overwriting there will probably be a window 
                #   in which both oldpath and newpath refer to the file being renamed."
                # see http://www.linuxmanpages.com/man2/rename.2.php
                # create a "MOVING" flag file
                moving_flag_path = utils.getLogFilePath(site_id, "MOVING")
                open(moving_flag_path, 'w').close()
                os.rename(current_file_path, dest_file_path)
                os.remove(moving_flag_path)
                self.filesMap[site_id] = open(utils.getLogFilePath(site_id, "current"), "a")
                # update the last rotation flag
                self.touchLastRotationFile(site_id, create_only=False)

    def writeToLogFile(self, site_id, line):
        f = self.filesMap[site_id]
        f.write("%s\n" % line)
        f.flush()

    def loadLastRotationTS(self, site_id):
        last_rotation_file = utils.getLogFilePath(site_id, "LAST_ROTATION")
        f = open(last_rotation_file, "r")
        timestamp = float(f.read())
        f.close()
        return timestamp

    def touchLastRotationFile(self, site_id, create_only=False):
        # generate last rotation file
        last_rotation_file = utils.getLogFilePath(site_id, "LAST_ROTATION")
        timestamp_str = repr(time.time())
        if (create_only and not os.path.exists(last_rotation_file)) or (not create_only):
            f = open(last_rotation_file, "w")
            f.write(timestamp_str)
            f.close()

    def prepareLogDirAndFiles(self):
        for site_id in mongo_client.getSiteIds():
            if not self.filesMap.has_key(site_id):
                site_log_dir = utils.getLogDirPath(site_id)
                if not os.path.isdir(site_log_dir):
                    os.mkdir(site_log_dir)
                current = utils.getLogFilePath(site_id, "current")
                self.filesMap[site_id] = open(current, "a")
                self.touchLastRotationFile(site_id, create_only=True)

    def writeEntry(self, action, site_id, *args):
        timestamp = time.time()
        if timestamp <> self.last_timestamp:
            self.count = 0
        else:
            self.count += 1
        self.last_timestamp = timestamp
        timestamp_plus_count = "%r+%s" % (timestamp, self.count)
        line = ",".join((timestamp_plus_count, action) + args)
        if settings.print_raw_log:
            print "RAW LOG:", line
        self.writeToLogFile(site_id, line)





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
        logWriter.writeEntry("V", args["site_id"],
                        args["user_id"], self.tuijianbaoid, args["item_id"])
        return {"code": 0}


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
        logWriter.writeEntry("AF", args["site_id"], 
                        args["user_id"], self.tuijianbaoid, 
                        args["item_id"])
        return {"code": 0}


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
        logWriter.writeEntry("RF", args["site_id"], 
                        args["user_id"], self.tuijianbaoid, args["item_id"])
        return {"code": 0}


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
        logWriter.writeEntry("RI", args["site_id"], 
                        args["user_id"], self.tuijianbaoid, args["item_id"],
                        args["score"])
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
        logWriter.writeEntry("ASC", args["site_id"],
                        args["user_id"], self.tuijianbaoid, args["item_id"])
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
        logWriter.writeEntry("RSC", args["site_id"],
                        args["user_id"], self.tuijianbaoid, args["item_id"])
        return {"code": 0}


class PlaceOrderHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("order_content", True), # use comma to separate items
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        if args["site_id"] not in customers:
            return {"code": 2}
        else:
            logWriter.writeEntry("PO", args["site_id"],  
                            args["user_id"], args["item_id"])
            return {"code": 0}


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
        logWriter.writeEntry("RecVAV", args["site_id"],
                        req_id,
                        args["user_id"], self.tuijianbaoid, args["item_id"],
                        args["amount"])

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


class RecommendBasedOnBrowsingHistoryHandler(APIHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", True),
         ("browsing_history", False),
         ("amount", True),
         ("callback", False)
        ))

    def logRecommendationRequest(self, args, req_id):
        browsing_history = "|".join(args["browsing_history"].split(","))
        logWriter.writeEntry("RecBOBH", args["site_id"], 
                        req_id,
                        args["user_id"], self.tuijianbaoid, args["amount"],
                        args["browsing_history"])

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
        topn = mongo_client.recommend_based_on_browsing_history(site_id, browsing_history, amount)
        req_id = generateReqId()
        self.logRecommendationRequest(args, req_id)
        return {"code": 0, "topn": topn, "req_id": req_id}



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
