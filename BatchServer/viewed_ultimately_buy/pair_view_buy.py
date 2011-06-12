import sys
import logging


logger = logging.getLogger("PairViewBuy")


def emit_pairs(pairs, v_items, b_item):
    for v_item in v_items:
        pairs.append((v_item, b_item))


def output(f_output, user_id, behaviors):
    v_items = []
    pairs = []
    for b, item_id in behaviors:
        if b == "V":
            v_items.append(item_id)
        elif b == "PLO":
            b_item = item_id
            emit_pairs(pairs, v_items, b_item)
    pairs_set = set(pairs)
    for pair in pairs_set:
        f_output.write("%s,%s\n" % pair)
    f_output.flush()


def pair_view_buy(input_path, output_path):
    last_user_id = None
    behaviors = []

    f_output = open(output_path, "w")
    for line in open(input_path, "r"):
        user_id, timestamp, behavior, item_id = line.strip().split(",")
        #logger.critical("UBI:%s,%s,%s" % (user_id, behavior, item_id))
        if last_user_id <> user_id:
            #logger.critical("OUTPUT:%s,%s" % (last_user_id, behaviors))
            output(f_output, last_user_id, behaviors)
            last_user_id = user_id
            behaviors = []
        behaviors.append((behavior, item_id))

    output(f_output, last_user_id, behaviors)
    f_output.close()
