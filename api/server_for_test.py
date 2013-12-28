#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
import server
import tornado.web


settings = server.settings
settings.server_port = 15588

class ChangeSettingsHandler(tornado.web.RequestHandler):
    def get(self):
        key = self.request.arguments["key"][0]
        value = eval(self.request.arguments["value"][0])
        setattr(server.settings, key, value)
        self.write('{"code": 0}')

server.handlers.append((r"/1.0/test_only/change_settings", ChangeSettingsHandler))
print server.handlers

# re-create database and upload similarities for test purpose.
import pymongo
from common import utils
connection = pymongo.Connection(settings.mongodb_host)
connection.drop_database(utils.getSiteDBName("tester"))
utils.UploadItemSimilarities(connection, "tester", type="V")("item_similarities_v_for_test")
utils.UploadItemSimilarities(connection, "tester", type="PLO")("item_similarities_plo_for_test")
utils.UploadItemSimilarities(connection, "tester", type="BuyTogether")("item_similarities_buy_together_for_test")

if __name__ == "__main__":
    server.main()
