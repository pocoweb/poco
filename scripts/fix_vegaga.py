#!/usr/bin/env python

import pymongo
import sys

if len(sys.argv) != 2:
    print "Usage: vegaga.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]

conn = pymongo.Connection(mongodb_host)
logs = conn["tjbsite_vegaga"]["raw_logs"]
print logs.count()
print logs.find({"behavior": "PLO"}).count()

import csv

rows = csv.reader(open('/tmp/ids.csv', 'rU'), delimiter=',')
skus = {}
_skus = {}
for row in rows:
    skus[row[1]] = row[0]
    _skus[row[0]] = row[1]


#ids_txt = open('/tmp/ids.txt', 'rU')
#ids = ids_txt.read().split('\n')

#update_count = 0
#for _id in ids:
#    if _skus.has_key(_id):
#       update_count += 1
#        logs.update({'order_content.item_id': _skus[_id]}, {'$set':{'order_content.$.item_id':_id}}, multi=True)
#        print 'DONE ', update_count, _skus[_id], ' -> ', _id

order_count = 0
item_count = 0
err_count = 0
suc_count = 0
for log in logs.find({'behavior':'PLO'},{'order_content.item_id':1}):
    order_count += 1
    for line in log['order_content']:
        item_count += 1

        if len(line['item_id']) > 4:
            err_count += 1
            print "ERR ", err_count, order_count, item_count, log['_id'], line, "id is: ", skus[line['item_id']]
            #line['item_id'] = skus[line['item_id']]
            #logs.save(log)
        else:
            suc_count += 1
            print "SUC ", suc_count, order_count, item_count, log['_id'], line
