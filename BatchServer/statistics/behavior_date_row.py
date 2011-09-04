import simplejson as json
import datetime


def getDateStr(timestamp):
    try:
        dt = datetime.datetime.fromtimestamp(timestamp)
    except:
        raise Exception("Can't pase timestamp: %r" % (timestamp,))
    date_str = dt.strftime("%Y-%m-%d")
    return date_str


def behavior_date_row(input_path, output_path):
    f = open(output_path, "w")
    for line in open(input_path, "r"):
        row = json.loads(line.strip())
        req_id = row.get("req_id", "null")
        tjbid = row.get("tjbid", "null")
        date_str = getDateStr(row["created_on"])
        f.write("%s,%s\n" % (row["behavior"], date_str, ))
    f.close()
