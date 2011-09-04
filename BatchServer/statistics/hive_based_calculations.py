# coding=utf-8
import sys
#sys.path.insert(0, "/Users/sun/tmp/kuaishubao_calc/hive-0.7.1-bin/lib/py")
import os.path
import simplejson as json
import datetime
import logging

from hive_service import ThriftHive
from hive_service.ttypes import HiveServerException
from thrift import Thrift
from thrift.transport import TSocket
from thrift.transport import TTransport
from thrift.protocol import TBinaryProtocol

from common.utils import getSiteDBCollection
from common.utils import smart_split

logger = logging.getLogger("HiveBased")

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
    output1 = []
    for item in output:
        if isinstance(item, unicode):
            output1.append(item.encode("utf-8"))
        else:
            output1.append(item)
    out_f.write("%s\n" % DELIMITER.join(output1))
    out_f.flush()


def log_function(function):
    def wrapped_function(*arg, **kws):
        logger.info("HIVE_START %s" % function.__name__)
        result = function(*arg, **kws)
        logger.info("HIVE_END %s" % function.__name__)
    return wrapped_function


@log_function
def convert_recommendation_logs(work_dir, backfilled_raw_logs_path):
    output_file_path = os.path.join(work_dir, "recommendation_logs_comma_separated")
    out_f = open(output_file_path, "w")
    for line in open(backfilled_raw_logs_path, "r"):
        row = json.loads(line.strip())
        if row["behavior"].startswith("Rec"):
            calendar_info = getCalendarInfo(row["created_on"])
            date_str = calendar_info["date_str"]
            if row["is_empty_result"]:
                is_empty_result = "TRUE"
            else:
                is_empty_result = "FALSE"

            output = [date_str, repr(row["created_on"]), row["behavior"], row["req_id"], is_empty_result]
            output_a_row(out_f, output)
    out_f.close()


@log_function
def load_recommendation_logs(work_dir, client):
    input_file_path = os.path.join(work_dir, "recommendation_logs_comma_separated")
    client.execute("DROP TABLE recommendation_logs")
    client.execute("CREATE TABLE recommendation_logs ( "
                     "date_str STRING, "
                     "created_on DOUBLE, "
                     "uniq_order_id STRING, "
                     "behavior STRING, "
                     "req_id STRING, "
                     "is_empty_result BOOLEAN "
                     ")"
                     "ROW FORMAT DELIMITED "
                     "FIELDS TERMINATED BY ',' "
                     "STORED AS TEXTFILE")
    client.execute("LOAD DATA LOCAL INPATH '%s' OVERWRITE INTO TABLE recommendation_logs" % input_file_path)


@log_function
def calc_recommendations_request_by_type(site_id, connection, client):
    client.execute("DROP TABLE   recommendations_request_by_type")
    client.execute("CREATE TABLE recommendations_request_by_type ( "
                   " date_str STRING, "
                   " behavior STRING, "
                   " count    INT "
                   ")")
    client.execute("INSERT OVERWRITE TABLE recommendations_request_by_type "
                   "SELECT date_str, behavior, COUNT(*) "
                   "FROM recommendation_logs "
                   "GROUP BY date_str, behavior")


@log_function
def calc_recommendations_show_by_type(site_id, connection, client):
    client.execute("DROP TABLE   recommendations_show_by_type")
    client.execute("CREATE TABLE recommendations_show_by_type ( "
                   " date_str STRING, "
                   " behavior STRING, "
                   " count    INT "
                   ")")
    client.execute("INSERT OVERWRITE TABLE recommendations_show_by_type "
                   "SELECT date_str, behavior, COUNT(*) "
                   "FROM recommendation_logs "
                   "WHERE NOT is_empty_result "
                   "GROUP BY date_str, behavior")


@log_function
def calc_click_rec_by_type(site_id, connection, client):
    client.execute("DROP TABLE click_rec_by_type")
    client.execute("CREATE TABLE click_rec_by_type ( "
                   " date_str STRING, "
                   " behavior STRING, "
                   " count    INT "
                   ")")
    client.execute("INSERT OVERWRITE TABLE click_rec_by_type "
                   "SELECT date_str, behavior, COUNT(*) "
                   "FROM "
                   "   (SELECT brl.date_str, rl.behavior "
                   "   FROM recommendation_logs rl "
                   "   JOIN backfilled_raw_logs brl ON (rl.req_id = brl.req_id) "
                   '   WHERE brl.behavior = "ClickRec") a '
                   "GROUP BY date_str, behavior")


@log_function
def calc_recommendations_by_type_n_click_rec_by_type(site_id, connection, client):
    calc_recommendations_request_by_type(site_id, connection, client)
    calc_recommendations_show_by_type(site_id, connection, client)
    calc_click_rec_by_type(site_id, connection, client)
    
    client.execute("SELECT rrbt.date_str, rrbt.behavior, rrbt.count AS recommendation_request_count, rsbt.count AS recommendation_show_count, cbt.count AS click_rec_count, cbt.count / rsbt.count "
                   "FROM recommendations_request_by_type rrbt "
                   "LEFT OUTER JOIN recommendations_show_by_type rsbt ON (rrbt.date_str = rsbt.date_str AND rrbt.behavior = rsbt.behavior) "
                   "LEFT OUTER JOIN click_rec_by_type cbt ON (rrbt.date_str = cbt.date_str AND rrbt.behavior = cbt.behavior) "
                   )

    data_map = {}
    for row in yieldClientResults(client):
        row_dict = result_as_dict(row, ["date_str", "behavior", ("recommendation_request_count", as_int), 
                                                                ("recommendation_show_count", as_int),
                                                                ("click_rec_count", as_int), 
                                                                ("click_rec_show_ratio", as_float)])
        data = data_map.setdefault(row_dict["date_str"], {"date_str": row_dict["date_str"]})
        behavior_lower = row_dict["behavior"].lower()
        data["recommendation_request_count_" + behavior_lower] = row_dict["recommendation_request_count"]
        data["recommendation_show_count_" + behavior_lower] = row_dict["recommendation_show_count"]
        data["click_rec_count_" + behavior_lower] = row_dict["click_rec_count"]
        data["click_rec_show_ratio_" + behavior_lower] = row_dict["click_rec_show_ratio"]

    for data in data_map.values():
        upload_statistics(site_id, connection, client, data)


@log_function
def convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path):
    output_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    out_f = open(output_file_path, "w")
    for line in open(backfilled_raw_logs_path, "r"):
        row = json.loads(line.strip())
        calendar_info = getCalendarInfo(row["created_on"])
        date_str = calendar_info["date_str"]
        hour = calendar_info["hour"]
        uniq_order_id = row.get("uniq_order_id", "")
        output = [date_str, repr(hour), repr(row["created_on"]), uniq_order_id,
                  row["filled_user_id"], row["behavior"], row["tjbid"]]
        if row["behavior"] == "V":
            output += [row["item_id"], "0", "0", "0"]
            output_a_row(out_f, output)
        elif row["behavior"] == "PLO":
            for order_item in row["order_content"]:
                output1 = output + [order_item["item_id"], str(order_item["price"]), str(order_item["amount"]), "0"]
                output_a_row(out_f, output1)
        elif row["behavior"] == "ClickRec":
            output += [row["item_id"], "0", "0", row["req_id"]]
            output_a_row(out_f, output)

    out_f.close()


@log_function
def load_backfilled_raw_logs(work_dir, client):
    input_file_path = os.path.join(work_dir, "backfilled_raw_logs_ctrl_a_separated")
    client.execute("DROP TABLE backfilled_raw_logs")
    client.execute("CREATE TABLE backfilled_raw_logs ( "
                     "date_str STRING, "
                     "hour INT, "
                     "created_on DOUBLE, "
                     "uniq_order_id STRING, "
                     "filled_user_id STRING, "
                     "behavior STRING, "
                     "tjbid STRING, "
                     "item_id STRING,"
                     "price FLOAT, "
                     "amount INT, "
                     "req_id STRING "
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


def as_int(string):
    if string == "NULL":
        return None
    else:
        return int(string)

def as_float(string):
    if string == "NULL":
        return None
    else:
        return float(string)


def result_as_dict(result, columns):
    result_dict = {}
    for idx in range(len(result)):
        column = columns[idx]
        if isinstance(column, tuple):
            column_name, converter = column
            value = converter(result[idx])
        else:
            column_name = column
            value = result[idx]
        result_dict[column_name] = value
    return result_dict


@log_function
def calc_daily_order_money_related(site_id, connection, client):
    client.execute("SELECT a.date_str, COUNT(*), AVG(a.total_money), SUM(a.total_money) "
                   "FROM (SELECT date_str, uniq_order_id,  SUM(price * amount) AS total_money "
                   '      FROM backfilled_raw_logs WHERE behavior="PLO" GROUP BY date_str, uniq_order_id) a '
                   "GROUP BY a.date_str ")
    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", ("order_count", as_int), ("avg_order_total", as_float), ("total_sales", as_float)])
        upload_statistics(site_id, connection, client, data)


def calc_ClickRec_by_type(site_id, connection, client):
    pass


@log_function
def calc_kedanjia_without_rec(site_id, connection, client):
    client.execute("SELECT a.date_str, COUNT(*), AVG(a.total_money), SUM(a.total_money) "
                   "FROM (SELECT date_str, uniq_order_id,  SUM(price * amount) AS total_money "
                   '      FROM place_order_with_rec_info pow '
                   '      WHERE NOT is_rec_item '
                   '      GROUP BY date_str, uniq_order_id '
                   '     ) a '
                   "GROUP BY a.date_str ")

    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", ("order_count_no_rec", as_int), ("avg_order_total_no_rec", as_float), 
                                                ("total_sales_no_rec", as_float)])
        upload_statistics(site_id, connection, client, data)


@log_function
def calc_kedanjia_with_rec(site_id, connection, client):
    client.execute("SELECT a.date_str, COUNT(*), AVG(a.total_money), SUM(a.total_money) "
                   "FROM (SELECT date_str, uniq_order_id,  SUM(price * amount) AS total_money "
                   '      FROM place_order_with_rec_info pow '
                   '      GROUP BY date_str, uniq_order_id '
                   '     ) a '
                   "GROUP BY a.date_str ")
    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", ("order_count", as_int), ("avg_order_total", as_float), ("total_sales", as_float)])
        upload_statistics(site_id, connection, client, data)


@log_function
def calc_place_order_with_rec_info(site_id, connection, client):
    client.execute("DROP TABLE   place_order_with_rec_info")
    client.execute("CREATE TABLE place_order_with_rec_info ( "
                     "date_str STRING, "
                     "hour INT, "
                     "uniq_order_id DOUBLE, "
                     "filled_user_id STRING, "
                     "tjbid STRING, "
                     "item_id STRING,"
                     "price FLOAT, "
                     "amount INT, "
                     "has_rec_item BOOLEAN, "
                     "is_rec_item BOOLEAN "
                     ")"
                     "ROW FORMAT DELIMITED "
                     "FIELDS TERMINATED BY ',' "
                     "STORED AS TEXTFILE")
    client.execute("INSERT OVERWRITE TABLE place_order_with_rec_info "
                   "  SELECT a.date_str, a.hour, a.uniq_order_id, a.filled_user_id, "
                   "         a.tjbid, a.item_id, a.price, a.amount, a.rb1_uoid IS NOT NULL, "
                   "                         (a.rb1_uoid IS NOT NULL AND a.rb1_item_id == a.item_id)  "
                   "  FROM "
                   "   (SELECT DISTINCT brl.date_str, brl.hour, brl.uniq_order_id, brl.filled_user_id, "
                   "    brl.tjbid, brl.item_id, brl.price, brl.amount, rb1.uniq_order_id AS rb1_uoid, rb1.item_id AS rb1_item_id "
                   "    FROM rec_buy rb1 "
                   "    RIGHT OUTER JOIN backfilled_raw_logs brl ON (rb1.uniq_order_id = brl.uniq_order_id) "
                   '    WHERE brl.behavior = "PLO" '
                   "   ) a"
                   )


@log_function
def calc_click_rec_buy(site_id, connection, client):
    client.execute("add FILE %s" % getMapperFilePath("find_rec_buy.py"))
    client.execute("DROP TABLE rec_buy")
    client.execute("CREATE TABLE rec_buy ( "
                   "         created_on DOUBLE, "
                   "         uniq_order_id STRING, "
                   "         user_id    STRING, "
                   "         item_id    STRING  "
                   " ) ")
    client.execute("INSERT OVERWRITE TABLE rec_buy "
                   "SELECT TRANSFORM (filled_user_id, created_on, uniq_order_id, behavior, item_id, price, amount) "
                   "       USING 'python find_rec_buy.py' "
                   "       AS (created_on, uniq_order_id, user_id, item_id) "
                   "FROM (SELECT brl.filled_user_id, brl.created_on, brl.uniq_order_id, brl.behavior, brl.item_id, brl.price, brl.amount "
                   "FROM backfilled_raw_logs brl "
                   'WHERE brl.behavior = "ClickRec" OR brl.behavior = "PLO" OR brl.behavior="V" '
                   'ORDER BY filled_user_id, uniq_order_id) a ')


@log_function
def calc_avg_item_amount(site_id, connection, client):
    client.execute("SELECT a.date_str, AVG(a.amount) AS avg_item_amount "
                   "FROM (SELECT uniq_order_id, date_str, SUM(amount) AS amount "
                   "      FROM backfilled_raw_logs brl "
                   '      WHERE behavior = "PLO"'
                   "      GROUP BY uniq_order_id, date_str) a "
                   "GROUP BY a.date_str"
    )
    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", ("avg_item_amount", as_float)])
        upload_statistics(site_id, connection, client, data)


@log_function
def calc_unique_sku(site_id, connection, client):
    client.execute("SELECT date_str, AVG(sku) AS avg_unique_sku "
                   "FROM (SELECT uniq_order_id, date_str, COUNT(DISTINCT item_id) AS sku "
                   "      FROM backfilled_raw_logs brl "
                   '      WHERE behavior = "PLO" '
                   "      GROUP BY uniq_order_id, date_str) a "
                   "GROUP BY date_str"
    )
    for row in yieldClientResults(client):
        data = result_as_dict(row, ["date_str", ("avg_unique_sku", as_float)])
        upload_statistics(site_id, connection, client, data)


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
                       "(SELECT TRANSFORM (created_on, filled_user_id, behavior, tjbid, item_id) "
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
    convert_backfilled_raw_logs(work_dir, backfilled_raw_logs_path)
    load_backfilled_raw_logs(work_dir, client)

    convert_recommendation_logs(work_dir, backfilled_raw_logs_path)
    load_recommendation_logs(work_dir, client)
    #load_items(connection, site_id, work_dir, client)
    #calc_daily_item_pv_coverage(client)

    #calc_daily_order_money_related(site_id, connection, client)

    calc_unique_sku(site_id, connection, client)
    calc_avg_item_amount(site_id, connection, client)
    
    calc_click_rec_buy(site_id, connection, client)
    calc_place_order_with_rec_info(site_id, connection, client)

    calc_kedanjia_with_rec(site_id, connection, client)
    calc_kedanjia_without_rec(site_id, connection, client)

    calc_recommendations_by_type_n_click_rec_by_type(site_id, connection, client)


def hive_based_calculations(connection, site_id, work_dir, backfilled_raw_logs_path, 
                        do_calculations=do_calculations):

    transport = TSocket.TSocket('localhost', 10000)
    transport = TTransport.TBufferedTransport(transport)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    client = ThriftHive.Client(protocol)
    transport.open()
    do_calculations(connection, site_id, work_dir, backfilled_raw_logs_path, client)
    transport.close()


