def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def output(f, rows, n_limit):
    rows.sort(lambda a, b: sign(b[2] - a[2]))
    if len(rows) > n_limit:
        rows = rows[:n_limit]
    for row in rows:
        f.write("%s,%s,%s\n" % row)
    f.flush()


def extract_top_n(input_path, output_path, n_limit):
    last_item1 = None
    last_rows = []
    f_output = open(output_path, "w")
    for line in open(input_path, "r"):
        item1, item2, sim = line.split(",")
        sim = float(sim)
        if last_item1 != item1:
            output(f_output, last_rows, n_limit)
            last_item1 = item1
            last_rows = []
        last_rows.append((item1, item2, sim))
    f_output.close()
