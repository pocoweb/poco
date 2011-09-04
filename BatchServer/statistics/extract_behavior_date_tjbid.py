import simplejson as json
import datetime


def getDateStr(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    date_str = dt.strftime("%Y-%m-%d")
    return date_str


def extract_behavior_date_tjbid(input_path, output_path):
    f = open(output_path, "w")
    for line in open(input_path, "r"):
        row = json.loads(line.strip())
        if row.has_key("tjbid"):
            tjbid = row["tjbid"]
            date_str = getDateStr(row["created_on"])
            f.write("%s,%s,%s\n" % (row["behavior"], date_str, tjbid))
    f.close()
