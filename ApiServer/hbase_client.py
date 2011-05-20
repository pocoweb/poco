from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol import TBinaryProtocol
from hbase.ttypes import Mutation
from hbase import Hbase

import md5

import simplejson as json

import settings

transport = TBufferedTransport(
        TSocket(settings.hbase_thrift_host, settings.hbase_thrift_port))
transport.open()
protocol = TBinaryProtocol.TBinaryProtocol(transport)

client = Hbase.Client(protocol)

ITEM_SIMILARITY_TABLE = "demo1_item_similarities"

def doHash(id):
    return md5.md5(id).hexdigest()


def updateItem(item):
    the_id = md5.md5(item["customer_id"] + ":" + item["item_id"]).hexdigest()
    item_json = json.dumps(item)
    client.mutateRow("items", the_id, [Mutation(column="p:content", value=item_json)])

def recommend_viewed_also_view(customer_id, item_id, amount):
    # FIXME: we ignore customer_id currently
    row = client.getRow(ITEM_SIMILARITY_TABLE, doHash(item_id))
    #item_id1 = row[0].columns["p:item_id1"].value
    #print "ITEM_ID1:", item_id1
    if len(row) == 0:
        return []
    most_similar_items = json.loads(row[0].columns["p:mostSimilarItems"].value)
    if len(most_similar_items) > amount:
        topn = most_similar_items[:amount]
    else:
        topn = most_similar_items
    return topn


def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def recommend_based_on_browsing_history(customer_id, pref_ids, amount):
    if len(pref_ids) > 10:
        recent_pref_ids = pref_ids[-10:]
    else:
        recent_pref_ids = pref_ids

    rec_map = {}
    for pref_id in recent_pref_ids:
        recommended_items = recommend_viewed_also_view(customer_id, str(pref_id), 15)
        for rec_item, score in recommended_items:
            if int(rec_item) not in pref_ids:
                rec_map.setdefault(rec_item, [0,0])
                rec_map[rec_item][0] += float(score)
                rec_map[rec_item][1] += 1
    rec_tuples = []
    for key in rec_map.keys():
        score_total, count = rec_map[key][0], rec_map[key][1]
        rec_tuples.append((key, score_total / count))
    rec_tuples.sort(lambda a,b: sign(b[1] - a[1]))
    topn = [int(rec_tuple[0]) for rec_tuple in rec_tuples]
    if len(topn) > amount:
        topn = topn[:amount]
    return topn

