from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol import TBinaryProtocol
from hbase.ttypes import Mutation
from hbase import Hbase

import md5
import sys

import settings


customer_id = sys.argv[1]


transport = TBufferedTransport(
        TSocket(settings.hbase_thrift_host, settings.hbase_thrift_port))
transport.open()
protocol = TBinaryProtocol.TBinaryProtocol(transport)

client = Hbase.Client(protocol)

def initTable(customer_id, tableType):
	tableName = "%s_%s" % (customer_id, tableType)
	if not tableName in client.getTableNames():
		client.createTable(tableName,
		    [ColumnDescriptor(name="p")]
		)


# Items Table
initTable(customer_id, "items")

# User Action Table
# row-key: <customer-id>-<user-id>-timestamp
initTable(customer_id, "user_action")

# Item-Item Similarity Table
initTable(customer_id, "item_similarities")

