# coding=utf-8
import sys
sys.path.insert(0, "../../pylib")
import os.path
import simplejson as json
import datetime
import logging

from hive_service import ThriftHive
from hive_service.ttypes import HiveServerException
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol


def test():

    transport = TSocket.TSocket('localhost', 10000)
    transport = TTransport.TBufferedTransport(transport)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    client = ThriftHive.Client(protocol)
    transport.open()
    client.execute("SELECT 1;")
    print client.fetchOne()
    transport.close()

test()
