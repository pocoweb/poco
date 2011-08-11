from common.utils import getSiteDBCollection


def upload_count_behaviors(connection, site_id, input_path):
    for line in open(input_path, "r"):
        count, rest = line.strip().split()
        count = int(count)
        behavior, date_str = rest.split(",")
        statistics = getSiteDBCollection(connection, site_id, "statistics")
        row_in_db = statistics.find_one({"date": date_str})
        if row_in_db is None:
            row_in_db = {"date": date_str}
        row_in_db.setdefault("PV_V", 0)
        row_in_db.setdefault("PV_Rec", 0)
        row_in_db.setdefault("PV_PLO", 0)
        row_in_db.setdefault("ClickRec", 0)
        if behavior == "V":
            row_in_db["PV_V"] = count
        elif behavior == "PLO":
            row_in_db["PV_PLO"] = count
        elif behavior.startswith("Rec"):
            row_in_db["PV_Rec"] += count
        elif behavior == "ClickRec":
            row_in_db["ClickRec"] = count
        statistics.save(row_in_db)
