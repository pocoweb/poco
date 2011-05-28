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

import settings
import hbase_client

from utils import doHash


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
        #self.startRotationLoop()

    def startRotationLoop(self):
        self.doRotateFiles()
        tornado.ioloop.IOLoop.instance().add_timeout(
                time.time() + settings.rotation_interval, 
                self.startRotationLoop)

    def _generateDestFilePath(self, site_id):
        ts = time.time()
        while True:
            dest_file_name = repr(ts)
            dest_file_path = self.getLogFilePath(site_id, dest_file_name)
            if not os.path.exists(dest_file_path):
                break
            ts += 0.001
        return dest_file_path

    def doRotateFiles(self):
        # TODO: need a more scalable solution
        for site_id in hbase_client.getSiteIds():
            current_file_path = self.getLogFilePath(site_id, "current")
            dest_file_path = self._generateDestFilePath(site_id)
            # this marks that we are 
            # not sure if "mv" is atomic, if the new_path does not exist.
            # according to "However, when overwriting there will probably be a window 
            #   in which both oldpath and newpath refer to the file being renamed."
            # see http://www.linuxmanpages.com/man2/rename.2.php
            # create a "MOVING" flag file
            moving_flag_path = self.getLogFilePath(site_id, "MOVING")
            open(moving_flag_path, 'w').close()
            os.rename(current_file_path, dest_file_path)
            os.remove(moving_flag_path)
            self.filesMap[site_id].close()
            self.filesMap[site_id] = open(self.getLogFilePath(site_id, "current"), "a")

    def writeToLogFile(self, site_id, line):
        f = self.filesMap[site_id]
        f.write("%s\n" % line)
        f.flush()

    def getLogDirPath(self, site_id):
        return os.path.join(settings.log_directory, site_id)

    def getLogFilePath(self, site_id, file_name):
        return os.path.join(self.getLogDirPath(site_id), file_name)

    def prepareLogDirAndFiles(self):
        for site_id in hbase_client.getSiteIds():
            if not self.filesMap.has_key(site_id):
                site_log_dir = self.getLogDirPath(site_id)
                if not os.path.isdir(site_log_dir):
                    os.mkdir(site_log_dir)
                current = self.getLogFilePath(site_id, "current")
                self.filesMap[site_id] = open(current, "a")

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
    site_ids = hbase_client.getSiteIds()
    def the_method(self, args):
        if args["site_id"] not in site_ids:
            print args["site_id"], site_ids
            return {"code": 2}
        else:
            return m(self, args)
    return the_method


class ViewItemHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("item_id", True),
         ("user_id", True), # if no user_id, pass in "null"
         ("session_id", True),
         ("callback", False)
        )
    )

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry("V", args["site_id"],
                        args["user_id"], args["session_id"], args["item_id"])
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

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry("AF", args["site_id"], 
                        args["user_id"], args["session_id"], 
                        args["item_id"])
        return {"code": 0}


class RemoveFavoriteHandler(tornado.web.RequestHandler):
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
        logWriter.writeEntry("RF", args["site_id"], 
                        args["user_id"], args["session_id"], args["item_id"])
        return {"code": 0}


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

    @api_method
    @check_site_id
    def get(self, args):
        logWriter.writeEntry("RI", args["site_id"], 
                        args["user_id"], args["session_id"],args["item_id"],
                        args["score"])
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
        self.removeItem(args)
        return {"code": 0}


#class ClickRecItemHandler(tornado.web.RequestHandler):
#    ae = ArgumentExtractor(
#        (("site_id", True),
#         ("item_id", True),
#         ("user_id", True),
#         ("session_id", True),
#         ("rec_id", True),
#         ("rec_page", False),
#         ("callback", False)
#        )
#    )


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
        topn = hbase_client.recommend_viewed_also_view(args["site_id"], args["item_id"], 
                        int(args["amount"]))
        #topn = hbase_client.getCachedVAV(args["site_id"], args["item_id"]) 
                        #,int(args["amount"]))
        return {"code": 0, "topn": topn}


class RecommendBasedOnBrowsingHistoryHandler(tornado.web.RequestHandler):
    ae = ArgumentExtractor(
        (("site_id", True),
         ("user_id", False),
         ("browsing_history", False),
         ("amount", True),
         ("callback", False)
        ))

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
        topn = hbase_client.recommend_based_on_browsing_history(site_id, browsing_history, amount)
        return {"code": 0, "topn": topn}


application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/tui/viewItem", ViewItemHandler),
    (r"/tui/addFavorite", AddFavoriteHandler),
    (r"/tui/removeFavorite", RemoveFavoriteHandler),
    (r"/tui/rateItem", RateItemHandler),
    (r"/tui/removeItem", RemoveItemHandler),
    (r"/tui/updateItem", UpdateItemHandler),
    (r"/tui/viewedAlsoView", RecommendViewedAlsoViewHandler),
    (r"/tui/basedOnBrowsingHistory", RecommendBasedOnBrowsingHistoryHandler)
])

if __name__ == "__main__":
    application.listen(settings.server_port, settings.server_name)
    tornado.ioloop.IOLoop.instance().start()

