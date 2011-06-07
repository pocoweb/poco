# coding=utf-8
import sys
sys.path.insert(0, "../")
sys.path.insert(0, "../../")
import csv
import mongo_client


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
    item = {"item_id": row["id"], "item_name": row["商品名称"], 
              "price": row["商品价格"], "image_link": row["商品缩略图"], 
              "description": row["商品详情"],
              "item_link": "http://ecshop.tuijianbao.net/goods.php?id=%s" % row["id"]}
    mongo_client.updateItem(site_id, item)
