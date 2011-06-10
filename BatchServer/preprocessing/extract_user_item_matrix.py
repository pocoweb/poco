import simplejson as json


def v_extract_user_item_matrix(input_path, output_path):
    f_output = open(output_path, "w")
    for line in open(input_path, "r"):
        line = line.strip()
        content = json.loads(line)
        if content["behavior"] == "V":
            f_output.write("%s,%s\n" % (content["filled_user_id"], 
                                    content["item_id"]))
    f_output.close()


def plo_extract_user_item_matrix(input_path, output_path):
    f_output = open(output_path, "w")
    for line in open(input_path, "r"):
        line = line.strip()
        content = json.loads(line)
        if content["behavior"] == "PLO":
            item_ids = [order_content_row["item_id"] 
                    for order_content_row in content["order_content"]]
            for item_id in item_ids:
                f_output.write("%s,%s\n" % (content["filled_user_id"], item_id))
    f_output.close()
