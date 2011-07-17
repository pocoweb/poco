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
from common.utils import smart_split


def getCalendarInfo(timestamp):
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
    except:
        raise Exception("Can't parse timestamp: %r, %r" % (timestamp, type(timestamp)))
    result = {}
    result["date_str"] = dt.strftime("%Y-%m-%d")
    result["month"] = dt.month
    result["day"] = dt.day
    result["hour"] = dt.hour
    result["year"], result["weeknum"], result["weekday"] = dt.isocalendar()
    return result


DELIMITER = ','
def output_a_row(out_f, output):
    out_f.write("%s\n" % DELIMITER.join(output))
    out_f.flush()

def convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path):
    output_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    out_f = open(output_file_path, "w")
    for line in open(backfilled_raw_logs_path, "r"):
        row = json.loads(line.strip())
        calendar_info = getCalendarInfo(row["timestamp"])
        date_str = calendar_info["date_str"]
        hour = calendar_info["hour"]
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
                     "FIELDS TERMINATED BY ',' "
                     "STORED AS TEXTFILE")
    client.execute("add FILE %s" % getMapperFilePath("as_behavior_datestr_item_id.py"))
    client.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE backfilled_raw_logs" % input_file_path)


def yieldClientResults(client):
    while True:
        row = client.fetchOne()
        if (row == None or row == ''):
            break
        yield smart_split(row, "\t")


def upload_statistics(site_id, connection, client, data):
    c_statistics = getSiteDBCollection(connection, site_id, "statistics")
    date_str = data["date_str"]
    del data["date_str"]
    row_in_db = c_statistics.find_one({"date": date_str})
    if row_in_db is None:
        row_in_db = {"date": date_str}
    for key in data.keys():
        row_in_db.update(data)
    c_statistics.save(row_in_db)


def result_as_dict(result, column_names):
    result_dict = {}
    for idx in range(len(result)):
        result_dict[column_names[idx]] = result[idx]
    return result_dict


def calc_daily_order_money_related(site_id, connection, client):
    client.execute("SELECT a.date_str, COUNT(*), AVG(a.total_money), SUM(a.total_money) "
                   "FROM (SELECT date_str, timestamp_,  SUM(price * amount) AS total_money "
                   '      FROM backfilled_raw_logs WHERE behavior="PLO" GROUP BY date_str, timestamp_) a '
                   "GROUP BY a.date_str ")
    print "Date", "Order Count", "Average Order Amount", "Total Sales"
    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", "order_count", "avg_order_total", "total_sales"])
        data["order_count"] = int(data["order_count"])
        data["avg_order_total"] = float(data["avg_order_total"])
        data["total_sales"] = float(data["total_sales"])
        #print ",".join((data["date_str"], str(data["order_count"]), str(data["avg_order_total"]), str(data["total_sales"])))
        upload_statistics(site_id, connection, client, data)



def look_for_rec_buy(result_set):
    MAX_DIRECT_TIME = 48 * 3600
    MAX_INDIRECT_TIME = 24 * 7 * 3600
    last_user_id = None
    last_click_recs = {}
    already_viewed = {}
    for row in result_set:
        user_id, timestamp, behavior, item_id, price, amount = row
        timestamp = float(timestamp)
        if price != "NULL" and amount != "NULL":
            price = float(price)
            amount = int(amount)
        else:
            price = 0
            amount = 0
        date_str = getCalendarInfo(timestamp)["date_str"]
        hour = getCalendarInfo(timestamp)["hour"]

        if last_user_id != user_id:
            last_click_recs = {}
            already_viewed = {}
            last_user_id = user_id

        if behavior == "V":
            already_viewed[item_id] = timestamp
        elif behavior == "ClickRec":
            if not already_viewed.has_key(item_id):
                last_click_recs[item_id] = (timestamp, True)
            else:
                last_click_recs[item_id] = (timestamp, False)
        elif behavior == "PLO":
            if last_click_recs.has_key(item_id):
                click_ts, is_rec_first = last_click_recs[item_id]
                influence_type = None
                if (timestamp - click_ts) < MAX_DIRECT_TIME:
                    influence_type = "DIRECT"
                elif (timestamp - click_ts) < MAX_INDIRECT_TIME:
                    influence_type = "INDIRECT"
                if is_rec_first:
                    influence_type += "_REC_FIRST"
                else:
                    influence_type += "_REC_LATER"
                if influence_type is not None:
                    print "%s %s h: %s bought %s %s by recommendation %s hours ago. PricexAmount=%s x %s=%s" % (date_str, hour, user_id, item_id, influence_type, (timestamp - click_ts)/3600.0, price, amount, price * amount)

def calc_click_rec_buy(site_id, connection, client):
    client.execute("SELECT brl.filled_user_id, brl.timestamp_, brl.behavior, brl.item_id, brl.price, brl.amount "
                   "FROM backfilled_raw_logs brl "
                   'WHERE brl.behavior = "ClickRec" OR brl.behavior = "PLO" OR brl.behavior="V" '
                   'ORDER BY filled_user_id, timestamp_')
    look_for_rec_buy(yieldClientResults(client))


def calc_avg_item_amount(site_id, connection, client):
    client.execute("SELECT a.date_str, AVG(a.amount) AS avg_amount "
                   "FROM (SELECT timestamp_, date_str, SUM(amount) AS amount "
                   "      FROM backfilled_raw_logs brl "
                   '      WHERE behavior = "PLO"'
                   "      GROUP BY timestamp_, date_str) a "
                   "GROUP BY a.date_str"
    )
    print "Date", "Average Item Amount"
    for row in yieldClientResults(client):
        print ",".join([row[0], str(row[1])])



def calc_unique_sku(site_id, connection, client):
    client.execute("SELECT date_str, AVG(sku) AS avg_sku "
                   "FROM (SELECT timestamp_, date_str, COUNT(DISTINCT item_id) AS sku "
                   "      FROM backfilled_raw_logs brl "
                   '      WHERE behavior = "PLO" '
                   "      GROUP BY timestamp_, date_str) a "
                   "GROUP BY date_str"
    )
    #client.execute(#"SELECT date_str, AVG(amount) AS avg_amount "
    #               "SELECT timestamp_, date_str, SUM(amount) AS amount "
    #               "      FROM backfilled_raw_logs brl "
    #               "      GROUP BY timestamp_, date_str "
    #               #"GROUP BY date_str"
    #)
    print "Date", "Average Unique SKU"
    for row in yieldClientResults(client):
        print ",".join((row[0], str(row[1])))


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


def do_calculations(connection, site_id, work_dir, backfilled_raw_logs_path, client):
        load_backfilled_raw_logs(work_dir, client)
        #load_items(connection, site_id, work_dir, client)
        #calc_daily_item_pv_coverage(client)

        calc_daily_order_money_related(site_id, connection, client)


def hive_based_calculations(connection, site_id, work_dir, backfilled_raw_logs_path, do_calculations=do_calculations):
    convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path)
    try:
        transport = TSocket.TSocket('localhost', 10000)
        transport = TTransport.TBufferedTransport(transport)
        protocol = TBinaryProtocol.TBinaryProtocol(transport)

        client = ThriftHive.Client(protocol)
        transport.open()
        do_calculations(connection, site_id, work_dir, backfilled_raw_logs_path, client)
        transport.close()

    except Thrift.TException, tx:
        print '%s' % (tx.message)



