import sys
sys.path.insert(0, "/Users/sun/tmp/kuaishubao_calc/hive-0.7.1-bin/lib/py")
import os.path
import simplejson as json

from hive_service import ThriftHive
from hive_service.ttypes import HiveServerException
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

sys.path.insert(0, "../..")
from common.utils import getSiteDBCollection


DELIMITER = '\t'
def convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path):
    output_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    out_f = open(output_file_path, "w")
    for line in open(backfilled_raw_logs_path, "r"):
        row = json.loads(line.strip())
        if row["behavior"] == "V":
            output = [str(row["timestamp"]), row["filled_user_id"], row["behavior"],
                      row["tjbid"],row["item_id"]]
            out_f.write("%s\n" % DELIMITER.join(output))
            out_f.flush()
        elif row["behavior"] == "PLO":
            output = [str(row["timestamp"]), row["filled_user_id"], row["behavior"],
                      row["tjbid"]]
            for order_item in row["order_content"]:
                out_f.write("%s\n" % DELIMITER.join(output + [order_item["item_id"]]))
                out_f.flush()
    out_f.close()


def load_backfilled_raw_logs(work_dir, client):
    input_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    client.execute("DROP TABLE backfilled_raw_logs")
    client.execute("CREATE TABLE backfilled_raw_logs ( "
                     "timestamp_ DOUBLE, "
                     "filled_user_id STRING, "
                     "behavior STRING, "
                     "tjbid STRING, "
                     "item_id STRING)"
                     "ROW FORMAT DELIMITED "
                     "FIELDS TERMINATED BY '\t' "
                     "STORED AS TEXTFILE")
    client.execute("add FILE %s" % getMapperFilePath("as_behavior_datestr_item_id.py"))
    client.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE backfilled_raw_logs" % input_file_path)

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


def getMapperFilePath(file_name):
    return "add FILE %s" % os.path.join(os.path.dirname(os.path.abspath(__file__)), "mappers", file_name)

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


def hive_based_calculations(connection, site_id, work_dir, backfilled_raw_logs_path):
    convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path)
    try:
        transport = TSocket.TSocket('localhost', 10000)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        client = ThriftHive.Client(protocol)
        transport.open()

        load_backfilled_raw_logs(work_dir, client)
        load_items(connection, site_id, work_dir, client)

        calc_daily_item_pv_coverage(client)

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
