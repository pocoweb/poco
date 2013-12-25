from common.utils import getSiteDBCollection
from common.utils import sign


def updateRecord(connection, site_id, item_view_times_map, last_item_id1, last_rows):
    last_rows.sort(lambda a, b: sign(b[1] - a[1]))

    item1_total_views = item_view_times_map[last_item_id1]
    content_dict = {"item_id": last_item_id1,
                    "total_views": item1_total_views, "viewedUltimatelyBuys": []}
    for row in last_rows:
        item_id2, count = row
        content_dict["viewedUltimatelyBuys"].append(
            {"item_id": item_id2,
             "count": count,
             "percentage": count / item1_total_views})

    c_viewed_ultimately_buys = getSiteDBCollection(
        connection, site_id, "viewed_ultimately_buys")
    c_viewed_ultimately_buys.update(
        {"item_id": last_item_id1}, content_dict, upsert=True)


def upload_viewed_ultimately_buy(connection, site_id, item_view_times_path,
                                 view_buy_pairs_counted_path):
    item_view_times_map = {}
    for line in open(item_view_times_path, "r"):
        times, item_id = line.strip().split(" ")
        item_view_times_map[item_id] = float(times)

    last_item_id1 = None
    last_rows = []
    for line in open(view_buy_pairs_counted_path, "r"):
        count, item_pair = line.strip().split(" ")
        item_id1, item_id2 = item_pair.split(",")
        if last_item_id1 is None:
            last_item_id1 = item_id1
            last_rows = []
        elif last_item_id1 != item_id1:
            updateRecord(connection, site_id, item_view_times_map,
                         last_item_id1, last_rows)
            last_item_id1 = item_id1
            last_rows = []
        last_rows.append((item_id2, float(count)))

    if last_item_id1 is not None:
        updateRecord(connection, site_id, item_view_times_map,
                     last_item_id1, last_rows)
