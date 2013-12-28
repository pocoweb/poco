import os
import os.path
import settings


def make_similarities_bidirectional(input_path, output_path):
    f = open(output_path, "w")
    for line in open(input_path, "r"):
        i1, i2, s = line.strip().split(",")
        f.write("%s,%s,%s\n" % (i1, i2, s))
        f.write("%s,%s,%s\n" % (i2, i1, s))
    f.close()

