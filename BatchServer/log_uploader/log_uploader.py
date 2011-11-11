import os


LOG_FILE_ROOT = "log" # TODO, avoid this kind of hardcode


# 1. check each customer directory
# 2. if there is a current file and also other files.
# 3. copy other files to hdfs, move them to trash bin. 
for customer_directory in os.listdir(LOG_FILE_ROOT):
    cd_path = LOG_FILE_ROOT + "/" + customer_directory
    file_names = os.listdir(cd_path)
    if not "ROTATING" in file_names:
        if "current" in file_names:
            file_names.remove("current")
        os.system("hadoop dfs -copyFromLocal %s %s" % (local_path, remote_path))
