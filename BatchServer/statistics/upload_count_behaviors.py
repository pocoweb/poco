from common.utils import getSiteDBCollection


def upload_count_behaviors(connection, site_id, input_path):
    for line in open(input_path, "r"):
        count, rest = line.strip().split()
        count = int(count)
        behavior, date_str = rest.split(",")
        c_statistics = getSiteDBCollection(connection, site_id, "statistics")
        content_row = {
                "date": date_str,
                "PV_V": 0,
                "PV_Rec": 0,
                "PV_PLO": 0,
                "ClickRec": 0}
        if behavior == "V":
            content_row["PV_V"] = count
        elif behavior == "PLO":
            content_row["PV_PLO"] = count
        elif behavior.startswith("Rec"):
            content_row["PV_Rec"] = count
        elif behavior == "ClickRec":
            content_row["ClickRec"] = count
        c_statistics.update({"date": date_str}, {"$set": content_row}, upsert=True)
