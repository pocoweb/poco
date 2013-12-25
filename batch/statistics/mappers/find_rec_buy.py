import sys
import datetime


MAX_DIRECT_TIME = 24 * 7 * 3600
MAX_INDIRECT_TIME = 24 * 30 * 3600


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
    user_id, created_on, uniq_order_id, behavior, item_id, price, amount, req_id = line.strip().split("\t")
    created_on = float(created_on)
    if price != "NULL" and amount != "NULL":
        price = float(price.strip())
        amount = int(amount)
    else:
        price = 0
        amount = 0
    date_str = getCalendarInfo(created_on)["date_str"]
    hour = getCalendarInfo(created_on)["hour"]

    if last_user_id != user_id:
        last_click_recs = {}
        already_viewed = {}
        last_user_id = user_id

    if behavior == "V":
        already_viewed[item_id] = created_on
    elif behavior == "ClickRec":
        if item_id in already_viewed:
            last_click_recs[item_id] = (created_on, True, req_id)
        else:
            last_click_recs[item_id] = (created_on, False, req_id)
    elif behavior == "PLO":
        if item_id in last_click_recs:
            click_ts, is_rec_first, rec_req_id = last_click_recs[item_id]
            influence_type = None
            if (created_on - click_ts) < MAX_DIRECT_TIME:
                influence_type = "DIRECT"
            elif (created_on - click_ts) < MAX_INDIRECT_TIME:
                influence_type = "INDIRECT"
            if influence_type is not None:
                if is_rec_first:
                    influence_type += "_REC_FIRST"
                else:
                    influence_type += "_REC_LATER"
                print "\t".join([repr(created_on), uniq_order_id, user_id, item_id, rec_req_id])
