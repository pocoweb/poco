
# This script copies logs from local directory to hdfs, and 
import os
import os.path
import re
import time

import settings
import utils
import hbase_client

# TODO: see http://wiki.apache.org/hadoop/HDFS-APIs   Use the thrift API.
# TODO: check existence of daily path for only once

def ensureDFSDirectoryExistence(dfs_path):
    if not testDFSFileExistence(dfs_path):
        dfsMkdir(dfs_path)

def testDFSFileExistence(dfs_path):
    code = dfsExecCommand("test", "-e %s" % dfs_path)
    return code == 0

def dfsMkdir(dfs_path):
    dfsExecCommand("mkdir", dfs_path)

def dfsExecCommand(command, args):
    full_command = "%s dfs -%s %s" % (settings.hadoop_command, command, args)
    print full_command
    code = os.system(full_command)
    return code

def getDateStrFromTS(ts):
    return time.strftime("%Y-%m-%d", time.localtime(ts))


for site_id in hbase_client.getSiteIds():
    print "working on %s" % site_id
    os.chdir(utils.getLogDirPath(site_id))
    file_names = os.listdir(".")
    # if the "MOVING" file presents, 
    if "MOVING" not in file_names:
        hdfs_site_raw_log_dir = os.path.join(settings.hdfs_raw_log_dir, site_id)
        ensureDFSDirectoryExistence(hdfs_site_raw_log_dir)
        file_names = [file_name for file_name in file_names if re.match("[0-9]+\.[0-9]+", file_name)]
        for file_name in file_names:
            hdfs_site_daily_raw_log_dir = os.path.join(hdfs_site_raw_log_dir, getDateStrFromTS(float(file_name)))
            ensureDFSDirectoryExistence(hdfs_site_daily_raw_log_dir)
            dest_file_name_on_dfs = "%s_%s" % (settings.node_name, file_name)
            full_dest_path = os.path.join(hdfs_site_daily_raw_log_dir, dest_file_name_on_dfs)
            code = dfsExecCommand("copyFromLocal", "%s %s" % (file_name, full_dest_path))
            # only delete the local file when the file was copied to remote server successfully.
            if code == 0:
                print "rm %s" % file_name
