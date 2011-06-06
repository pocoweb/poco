#!/usr/bin/env python
import sys
sys.path.insert(0, "../")
from optparse import OptionParser

import pymongo
from common.utils import getSiteDBCollection, getSiteDB

import mongo_client

parser = OptionParser()
parser.add_option("-r", "--reset_db", dest="reset_db", help="reset all database of this site(use with caution)",
                  default="no")
parser.add_option("-i", "--site_id", dest="site_id", help="Site ID(required)", default=None)
parser.add_option("-n", "--site_name", dest="site_name", help="Site Name(required)", default=None)

(options, args) = parser.parse_args()

site_id, site_name = options.site_id, options.site_name
assert site_id is not None
assert site_name is not None

if options.reset_db == "yes":
    connection = pymongo.Connection()
    getSiteDBCollection(connection, site_id, "item_similarities").drop()
    getSiteDBCollection(connection, site_id, "raw_logs").drop()
    getSiteDB(connection, site_id).create_collection("raw_logs", {})
    getSiteDBCollection(connection, site_id, "raw_logs").ensure_index([("timestamp", -1)])
    #getSiteDB(connection, site_id).create_collection("raw_logs", {"capped": True, "size": 200 * 1048576})

mongo_client.updateSite(site_id, site_name)

