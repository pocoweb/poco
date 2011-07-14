import sys
#sys.path.insert(0, "/Users/sun/tmp/kuaishubao_calc/hive-0.7.1-bin/lib/py")
import os.path
import simplejson as json
import datetime

from hive_service import ThriftHive
from hive_service.ttypes import HiveServerException
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from common.utils import getSiteDBCollection


def getDateStrAndHour(timestamp):
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
    except:
        raise Exception("Can't parse timestamp: %r, %r" % (timestamp, type(timestamp)))
    result = {}
    result["date_str"] = dt.strftime("%Y-%m-%d")
    result["hour"] = dt.hour
    return date_str, hour


DELIMITER = '\t'
def output_a_row(out_f, output):
    out_f.write("%s\n" % DELIMITER.join(output))
    out_f.flush()

def convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path):
    output_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    out_f = open(output_file_path, "w")
    for line in open(backfilled_raw_logs_path, "r"):
        row = json.loads(line.strip())
        date_str, hour = getDateStrAndHour(row["timestamp"])
        output = [date_str, repr(hour), repr(row["timestamp"]),
                  row["filled_user_id"], row["behavior"], row["tjbid"]]
        if row["behavior"] == "V":
            output += [row["item_id"], "0", "0"]
            output_a_row(out_f, output)
        elif row["behavior"] == "PLO":
            for order_item in row["order_content"]:
                output1 = output + [order_item["item_id"], str(order_item["price"]), str(order_item["amount"])]
                output_a_row(out_f, output1)
        elif row["behavior"] == "ClickRec":
            output += [row["item_id"], "0", "0"]
            output_a_row(out_f, output)

    out_f.close()


def load_backfilled_raw_logs(work_dir, client):
    input_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    client.execute("DROP TABLE backfilled_raw_logs")
    client.execute("CREATE TABLE backfilled_raw_logs ( "
                     "date_str STRING, "
                     "hour INT, "
                     "timestamp_ DOUBLE, "
                     "filled_user_id STRING, "
                     "behavior STRING, "
                     "tjbid STRING, "
                     "item_id STRING,"
                     "price FLOAT, "
                     "amount INT "
                     ")"
                     "ROW FORMAT DELIMITED "
                     "FIELDS TERMINATED BY '\t' "
                     "STORED AS TEXTFILE")
    client.execute("add FILE %s" % getMapperFilePath("as_behavior_datestr_item_id.py"))
    client.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE backfilled_raw_logs" % input_file_path)



def calc_kedanjia(client):
    pass


'''
def load_items(connection, site_id, work_dir, client):
    items_file_path = os.path.join(work_dir, "items")
    items_file = open(items_file_path, "w")
    c_items = getSiteDBCollection(connection, site_id, "items")
    for item in c_items.find():
        if item["available"]:
            items_file.write("%s\n" % item["item_id"])
    items_file.close()
    client.execute("DROP TABLE items_")
    client.execute("CREATE TABLE items_ ( "
                   "   item_id STRING )  "
                   "ROW FORMAT DELIMITED "
                   " FIELDS TERMINATED BY '\t' "
                   " STORED AS TEXTFILE")
    client.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE items_" % items_file_path)
'''


def getMapperFilePath(file_name):
    return "add FILE %s" % os.path.join(os.path.dirname(os.path.abspath(__file__)), "mappers", file_name)

'''
# TODO: also: items which accessed 0 times
# TODO: how to handle yesterday
# TODO: is this left join correct?
def calc_daily_item_pv_coverage(client):
    client.execute("CREATE TABLE daily_item_pv_coverage_no_zero ("
                     "behavior STRING, "
                     "datestr STRING, "
                     "item_id STRING, "
                     "count INT ) ")
    client.execute("INSERT OVERWRITE TABLE daily_item_pv_coverage_no_zero "
                    "SELECT a.behavior, a.datestr, a.item_id, count(*) AS count FROM "
                       "(SELECT TRANSFORM (timestamp_, filled_user_id, behavior, tjbid, item_id) "
                           "USING 'python as_behavior_datestr_item_id.py' "
                           "AS (behavior, datestr, item_id) "
                           "FROM backfilled_raw_logs) a "
                    "GROUP BY a.behavior, a.datestr, a.item_id "
                    )
    client.execute("SELECT items_.item_id, a.* FROM "
                   "items_ "
                   "LEFT OUTER JOIN daily_item_pv_coverage_no_zero a ON (items_.item_id = a.item_id) "
                   "ORDER BY behavior, datestr, count"
                 )
    while True:
        row = client.fetchOne()
        if (row == None or row == ''):
            break
        print repr(row)
'''


def hive_based_calculations(connection, site_id, work_dir, backfilled_raw_logs_path):
    convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path)
    try:
        transport = TSocket.TSocket('localhost', 10000)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        client = ThriftHive.Client(protocol)
        transport.open()

        load_backfilled_raw_logs(work_dir, client)
        #load_items(connection, site_id, work_dir, client)
        #calc_daily_item_pv_coverage(client)

        transport.close()

    except Thrift.TException, tx:
        print '%s' % (tx.message)


if __name__ == "__main__":
    import pymongo
    connection = pymongo.Connection()
    hive_based_calculations(
            connection,
            "kuaishubao",
            "/Users/sun/projects/Tuijianbao/hg/BatchServer/work_dir",
            "/Users/sun/projects/Tuijianbao/hg/BatchServer/work_dir/backfilled_raw_logs")
