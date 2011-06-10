import logging


logger = logging.getLogger("emit_cooccurances")


def output_cooccurance(f, last_user, item_ids):
    if len(item_ids) > 800:
        logger.info("One User Skipped: id=", last_user, "len(item_ids)=", len(item_ids))
        return
    for i in xrange(0, len(item_ids)):
        for j in xrange(i+1, len(item_ids)):
            f.write("%s,%s\n" % (item_ids[i], item_ids[j]))
    f.flush()


def emit_cooccurances(input_path, output_path):
    last_user = None
    item_ids = []

    f = open(output_path, "w")

    count = 0
    for line in open(input_path):
        line = line.strip()
        count += 1
        if count % 5000 == 0:
            logger.debug("progress:", count / float(6185990) * 100)
        user, item_id = line.split(',')
        if user != last_user:
            if len(item_ids) <> 0:
                item_ids.sort()
                output_cooccurance(f, last_user, item_ids)
            item_ids = []
            last_user = user
        item_ids.append(item_id)

    f.close()
