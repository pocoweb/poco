import sys
import pymongo
from common.utils import getSiteDBCollection


if len(sys.argv) != 2:
    print "Usage: fix_db_indexes.py <mongodb_host>"
    sys.exit(1)
else:
    mongodb_host = sys.argv[1]


connection = pymongo.Connection(mongodb_host)


def fix_item_similarities_collections(connection, site_id):
    for similarity_type in ("V", "PLO", "BuyTogether"):
        c_item_similarities = getSiteDBCollection(connection, site_id, "item_similarities_%s" % similarity_type)
        c_item_similarities.drop_indexes()
        c_item_similarities.ensure_index("item_id", 1, background=True, unique=True)


def fix_items(connection, site_id):
    c_items = getSiteDBCollection(connection, site_id, "items")
    c_items.drop_indexes()
    c_items.ensure_index("item_name", 1, background=True, unique=False)
    c_items.ensure_index("item_id", 1, background=True, unique=False)#, drop_dups=True)


def fix_purchasing_history(connection, site_id):
    c_purchasing_history = getSiteDBCollection(connection, site_id, "purchasing_history")
    c_purchasing_history.drop_indexes()
    c_purchasing_history.ensure_index("user_id", "1", background=True, unique=True)


def fix_raw_logs(connection, site_id):
    c_raw_logs = getSiteDBCollection(connection, site_id, "raw_logs")
    c_raw_logs.drop_indexes()
    c_raw_logs.ensure_index("timestamp", -1, background=True, unique=False)


def fix_statistics(connection, site_id):
    c_statistics = getSiteDBCollection(connection, site_id, "statistics")
    c_statistics.drop_indexes()
    c_statistics.ensure_index("date", 1, background=True, unique=True)


def fix_viewed_ultimately_buys(connection, site_id):
    c_viewed_ultimately_buys = getSiteDBCollection(connection, site_id, 
            "viewed_ultimately_buys")
    c_viewed_ultimately_buys.drop_indexes()
    c_viewed_ultimately_buys.ensure_index("item_id", 1, background=True, unique=True)


def fix_calculation_records(connection, site_id):
    c_calculation_records = getSiteDBCollection(connection, site_id, 
            "calculation_records")
    c_calculation_records.drop_indexes()
    c_calculation_records.ensure_index("begin_timestamp", -1, background=True, unique=False)


def fix_tjb_db(connection):
    connection["tjb-db"]["sites"].ensure_index("site_id", 1, background=True, unique=True)
    connection["tjb-db"]["sites"].ensure_index("api_key", 1, background=True, unique=True)
    
    connection["tjb-db"]["users"].ensure_index("user_name", 1, background=True, unique=True)
    connection["tjb-db"]["admin-users"].ensure_index("user_name", 1, background=True, unique=True)


for site in connection["tjb-db"]["sites"].find():
    site_id = site["site_id"]
    print "Work on %s" % site_id
    # fix sites 
    fix_tjb_db(connection)

    # fix site related dbs.
    fix_item_similarities_collections(connection, site_id)
    fix_items(connection, site_id)
    fix_purchasing_history(connection, site_id)
    fix_raw_logs(connection, site_id)
    fix_statistics(connection, site_id)
    fix_viewed_ultimately_buys(connection, site_id)
    fix_calculation_records(connection, site_id)
