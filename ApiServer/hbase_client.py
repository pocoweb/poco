from thrift.transport.TSocket import TSocket
from thrift.transport.TTransport import TBufferedTransport
from thrift.protocol import TBinaryProtocol
from hbase.ttypes import Mutation
from hbase.ttypes import ColumnDescriptor
from hbase import Hbase

from utils import doHash

import simplejson as json

import settings

transport = TBufferedTransport(
        TSocket(settings.hbase_thrift_host, settings.hbase_thrift_port))
transport.open()
protocol = TBinaryProtocol.TBinaryProtocol(transport)

client = Hbase.Client(protocol)


def _calcItemId(site_id, item_id):
    return md5.md5(site_id + ":" + item_id).hexdigest()

def updateItem(site_id, item):
    tableName = _getItemsTable(site_id)
    the_id = _calcItemId(site_id, item["item_id"])
    item_json = json.dumps(item)
    client.mutateRow(tableName, the_id, 
         [Mutation(column="p:content", value=item_json),
          Mutation(column="p:available", value="true")])

def removeItem(site_id, item_id):
    tableName = _getItemsTable(site_id)
    the_id = _calcItemId(site_id, item_id)
    client.mutateRow(tableName, the_id,
        [Mutation(column="p:available", value="false")])

def _getItemsTable(site_id):
    return "%s_items" % site_id

def _getItemSimilaritiesTable(site_id):
    return "%s_item_similarities" % site_id

def _getBrowsingHistoryTable(site_id):
    return "%s_browsing_history" % site_id

def _calcReversedTimestamp(timestamp):
    return 99999999999.0 - timestamp

def insertBrowsingHistory(site_id, session_id, item_id, timestamp):
    tableName = _getBrowsingHistoryTable(site_id)
    # rowkey uses reversed timestamp, so the latest will be the first.
    rowkey = doHash(session_id) + ":%r" % _calcReversedTimestamp(timestamp)
    content = json.dumps({"item_id": item_id, "timestamp": timestamp, 
                          "session_id": session_id})
    client.mutateRow(tableName, rowkey, 
            [Mutation(column="p:content", value=content)])


def fetchRecentNBrowsingHistory(site_id, session_id, n=10):
    tableName = _getBrowsingHistoryTable(site_id)
    rowkey_prefix = doHash(session_id) + ":"
    scanner_id = client.scannerOpenWithPrefix(tableName, rowkey_prefix, ["p:content"])   
    row_results = client.scannerGetList(scanner_id, n)
    client.scannerClose(scanner_id)
    rows = [json.loads(row_result.columns["p:content"].value) for row_result in row_results]
    return rows


SITE_IDS = None
def reloadSiteIds():
    global SITE_IDS
    site_ids = []
    tableName = "sites"
    scanner_id = client.scannerOpen(tableName, "", ["p:site_id"])
    while True:
        row = client.scannerGet(scanner_id)
        if len(row) == 0:
            break
        else:
            site_ids.append(row[0].columns["p:site_id"].value)
    client.scannerClose(scanner_id)
    SITE_IDS = set(site_ids)


def getSiteIds():
    global SITE_IDS
    if SITE_IDS is None:
        reloadSiteIds()
    return SITE_IDS


def updateSite(site_id, site_name):
    tableName = "sites"
    rowkey = site_id
    client.mutateRow(tableName, rowkey,
                [Mutation(column="p:site_id", value=site_id), 
                 Mutation(column="p:site_name", value=site_name)])



def recommend_viewed_also_view(site_id, item_id, amount):
    tableName = _getItemSimilaritiesTable(site_id)
    row = client.getRow(tableName, doHash(item_id))
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


cache = {}
def getCachedVAV(site_id, history_item):
    global cache
    if not cache.has_key((site_id, history_item)):
        cache[(site_id, history_item)] = recommend_viewed_also_view(site_id, str(history_item), 15)
    return cache[(site_id, history_item)]

def calc_weighted_top_list_method1(site_id, browsing_history):
    if len(browsing_history) > 15:
        recent_history = browsing_history[:15]
    else:
        recent_history = browsing_history

    # calculate weighted top list from recent browsing history
    rec_map = {}
    for history_item in recent_history:
        recommended_items = recommend_viewed_also_view(site_id, str(history_item), 15)
        #recommended_items = getCachedVAV(site_id, str(history_item))
        for rec_item, score in recommended_items:
            if rec_item not in browsing_history:
                rec_map.setdefault(rec_item, [0,0])
                rec_map[rec_item][0] += float(score)
                rec_map[rec_item][1] += 1
    rec_tuples = []
    for key in rec_map.keys():
        score_total, count = rec_map[key][0], rec_map[key][1]
        rec_tuples.append((key, score_total / count))
    rec_tuples.sort(lambda a,b: sign(b[1] - a[1]))
    return [int(rec_tuple[0]) for rec_tuple in rec_tuples]


def calc_weighted_top_list_method2(site_id, pref_ids):
    # see "Programming Collective Intelligence P25"
    # FIXME: seems not work well for implicit rating?
    if len(pref_ids) > 10:
        recent_pref_ids = pref_ids[-10:]
    else:
        recent_pref_ids = pref_ids

    # calculate weighted top list from recent browsing history
    scores = {}
    totalSim = {}
    for pref_id in recent_pref_ids:
        recommended_items = recommend_viewed_also_view(site_id, str(pref_id), 15)
        for rec_item, score in recommended_items:
            if int(rec_item) not in pref_ids:
                scores.setdefault(rec_item, 0)
                scores[rec_item] += float(score)
                totalSim.setdefault(rec_item, 0)
                totalSim[rec_item] += float(score)
    rankings = [(score/totalSim[item], item) for item, score in scores.items()]
    print rankings
    rankings.sort()
    rankings.reverse()
    return [ranking[1] for ranking in rankings]    


def recommend_based_on_browsing_history(site_id, browsing_history, amount):
    topn = calc_weighted_top_list_method1(site_id, browsing_history) 
    if len(topn) > amount:
        topn = topn[:amount]
    return topn


def initTable(tableName, deleteOld=False):
    if tableName in client.getTableNames():
        if deleteOld:
            client.disableTable(tableName)
            client.deleteTable(tableName)
            client.createTable(tableName, [ColumnDescriptor(name="p")])
    else:
        client.createTable(tableName,
                [ColumnDescriptor(name="p")]
        )

