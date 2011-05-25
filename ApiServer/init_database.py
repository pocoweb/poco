#!/usr/bin/env python

from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol import TBinaryProtocol
from hbase.ttypes import Mutation
from hbase.ttypes import ColumnDescriptor
from hbase import Hbase

import md5
import sys

import utils
import settings

import hbase_client


if len(sys.argv) == 2:
    site_id = sys.argv[1]
    deleteOld = False
elif len(sys.argv) == 3 and sys.argv[2] == "deleteOld":
    site_id = sys.argv[1]
    deleteOld = True
else:
    print "Usage: %s <site_id> [deleteOld]" % sys.argv[0]
    print "deleteOld - delete the existing table first (use with caution)"
    sys.exit(1)


transport = TBufferedTransport(
        TSocket(settings.hbase_thrift_host, settings.hbase_thrift_port))
transport.open()
protocol = TBinaryProtocol.TBinaryProtocol(transport)

client = Hbase.Client(protocol)

def initSiteTable(site_id, tableType):
    tableName = utils.getSiteTableName(site_id, tableType)
    hbase_client.initTable(tableName)


# Items Table
initSiteTable(site_id, "items")

# User Action Table
# row-key: hash(<session-id>)-timestamp
# p:content
#initTable(site_id, "browsing_history")

# Item-Item Similarity Table
initSiteTable(site_id, "item_similarities")


