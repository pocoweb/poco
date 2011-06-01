import simplejson as json
import os
import sys
import pymongo

import settings


if len(sys.argv) <> 2:
    print "Usage: %s <site_id>" % sys.argv[0]
    sys.exit(1)
else:
    site_id = sys.argv[1]


# FIXME: should use another table instead of the working table.
TABLE_NAME = "%s_item_similarities" % site_id

connection = pymongo.Connection()
item_similarities = connection["tjb_%s" % site_id]["item_similarities"]
item_similarities.ensure_index([("item_id", pymongo.DESCENDING)])

import md5

def doHash(id):
    return md5.md5(id).hexdigest()


# TODO: maybe better use multiple-column way and a compressed way. and compare.

def insertSimOneRow():
    global last_item1, last_rows
    #client.mutateRow(TABLE_NAME, doHash(last_item1),
    #            [Mutation(column="p:item_id1", value=last_item1),
    #            Mutation(column="p:mostSimilarItems", value=json.dumps(last_rows))])
    item_similarities.save({"item_id": last_item1, "mostSimilarItems": last_rows})
    last_item1 = item_id1
    last_rows = []


print "Download data from HDFS"
hdfs_item_similarities_file_path = settings.hdfs_item_similarity_root_path + "/%s/item-similarities" % site_id
local_item_similarities_file_path = "%s/item-similarities" % settings.tmp_dir

dfs_copy_command = "%s dfs -copyToLocal %s %s" \
        % (settings.hadoop_command, hdfs_item_similarities_file_path, local_item_similarities_file_path)
print dfs_copy_command
os.system(dfs_copy_command)


print "Load data to Mongo ..."
# Load data
last_item1 = None
last_rows = []
count = 0
import time
t0 = time.time()
for line in open(local_item_similarities_file_path, "r"):
    count += 1
    if count % 40000 == 0:
        finished_ratio = count / float(2788821)
        estimated = (time.time() - t0) * ( 1 / finished_ratio - 1) / 60
        print "%s percentage, %s minutes remain" % ((finished_ratio * 100), estimated)

    item_id1, item_id2, similarity = line.split(",")
    similarity = float(similarity)
    if last_item1 is None:
        last_item1 = item_id1
        last_rows = []
    elif last_item1 != item_id1:
        insertSimOneRow()
    last_rows.append((item_id2, similarity))

if len(last_rows) != 0:
    insertSimOneRow()
