import pymongo
import datetime
import time

import getopt, sys

try:
    host = sys.argv[1]
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    print "give a site_name"
    sys.exit(2) 

print host

conn = pymongo.Connection("cube2")

def datetime2ts(datetime):
    return time.mktime(datetime.timetuple())

d0 = datetime.datetime(2011,8,9,0,0,0)
for i in range(24):
    d1 = d0 + datetime.timedelta(minutes=60 * i)
    d2 = d0 + datetime.timedelta(minutes=60 * (i+1))
    print "%s(%s) - %s" % (d1, datetime2ts(d1), d2), conn["tjbsite_"+host].raw_logs.find({"timestamp":{"$gt":datetime2ts(d1), "$lt":datetime2ts(d2)}}).count()
