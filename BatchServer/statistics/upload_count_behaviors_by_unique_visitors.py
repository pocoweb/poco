import pymongo
from common.utils import getSiteDBCollection


def upload_count_behaviors_by_unique_visitors(connection, site_id, input_path):
    for line in open(input_path, "r"):
        count, rest = line.strip().split()
        count = int(count)
        behavior, date_str = rest.split(",")
        statistics = getSiteDBCollection(connection, site_id, "statistics")
        row_in_db = statistics.find_one({"date": date_str})
        if row_in_db is None:
            row_in_db = {"date": date_str}
        row_in_db.setdefault("UV_V", 0)
        if behavior == "V":
            row_in_db["UV_V"] = count
        statistics.save(row_in_db)
