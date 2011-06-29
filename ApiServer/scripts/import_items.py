# coding=utf-8
import sys
sys.path.insert(0, "../")
sys.path.insert(0, "../../")
import csv
import pymongo

import settings

from mongo_client import MongoClient

mongo_client = MongoClient(pymongo.Connection(settings.mongodb_host))


site_id = sys.argv[1]
csv_file = sys.argv[2]

f = open(csv_file, "r")

reader = csv.reader(f)
fields = reader.next()
count = 0
for row in csv.DictReader(f, fieldnames=fields):
    count += 1
    if count % 1000 == 0:
        print count
    item = {"item_id": row["id"], "item_name": row["item_name"], 
              "price": row["price"], "image_link": row["image_link"], 
              "description": row["description"],
              "item_link": "goods.php?id=%s" % row["id"]}
    mongo_client.updateItem(site_id, item)
