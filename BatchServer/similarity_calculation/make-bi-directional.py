import os
import os.path
import utils

utils.reset_and_enter_tmp_dir()

os.system("hadoop dfs -copyToLocal /user/hdfs/item-similarity/demo1/part-r-00000 part-r-00000")

f = open("tmp1", "w")
for line in open("part-r-00000", "r"): # FIXME: consider the case of multiple files.
    i1, i2, s = line.split() 
    f.write("%s,%s,%s\n" % (i1, i2, s))
    f.write("%s,%s,%s\n" % (i2, i1, s))
f.close()

os.system("sort tmp1 > tmp2")

import extract_top_15
extract_top_15.run("tmp2", "step2")

os.system("rm tmp1 tmp2")

os.system("hadoop dfs -copyFromLocal /user/hdfs/item-similarity/demo1/item-similarities")
