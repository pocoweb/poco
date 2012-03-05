import sys
import datetime
import uuid
import pymongo


if len(sys.argv) != 2:
    print "Usage: fix_database.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]


connection = pymongo.Connection(mongodb_host)

import csv

rows = csv.reader(open('/tmp/ids.csv', 'rU'), delimiter=',')
skus = {}
for row in rows:
    skus[row[1]] = row[0]

count = 0
logs = connection["tjbsite_vegaga"]["raw_logs"]
for log in logs.find({'behavior':'PLO'},{'order_content.item_id':1}):
    for line in log['order_content']:
        if len(line['item_id']) > 4:
            count += 1
            print "NO ", count, line, "id is: ", skus[line['item_id']]
            line['item_id'] = skus[line['item_id']]
            logs.save(log)
