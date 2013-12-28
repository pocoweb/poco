
def format_item_similarities(input_path, output_path):
    f = open(output_path, "w")
    for line in open(input_path, "r"):
        count, another_part = line.strip().split(" ")
        f.write("%s,%s\n" % (another_part, count))
    f.close()
