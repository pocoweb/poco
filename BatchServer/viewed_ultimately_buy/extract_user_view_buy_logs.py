import simplejson as json


def extract_user_view_buy_logs(input_path, output_path):
    f_output = open(output_path, "w")
    for line in open(input_path, "r"):
        data = json.loads(line.strip())
        if data["behavior"] == "V":
            f_output.write("%s,%s,%s,%s\n" % (data["filled_user_id"].encode("utf-8"), data["created_on"], data["behavior"], data["item_id"]))
        elif data["behavior"] == "PLO":
            for order_content_row in data["order_content"]:
                f_output.write("%s,%s,%s,%s\n" % (data["filled_user_id"].encode("utf-8"), data["created_on"],data["behavior"], order_content_row["item_id"]))
        f_output.flush()
    f_output.close()
