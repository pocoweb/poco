import sys
import datetime


MAX_DIRECT_TIME = 48 * 3600
MAX_INDIRECT_TIME = 24 * 7 * 3600


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


last_user_id = None
last_click_recs = {}
already_viewed = {}
for line in sys.stdin:
    user_id, timestamp, behavior, item_id, price, amount = line.strip().split("\t")
    timestamp = float(timestamp)
    if price != "NULL" and amount != "NULL":
        price = float(price.strip())
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
            if influence_type is not None:
                if is_rec_first:
                    influence_type += "_REC_FIRST"
                else:
                    influence_type += "_REC_LATER"
                print "\t".join([repr(timestamp), user_id, item_id])

