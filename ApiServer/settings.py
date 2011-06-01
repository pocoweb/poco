server_name = "localhost"
server_port = 5588
hbase_thrift_host = "localhost"
hbase_thrift_port = 9090
# If you set print_raw_log as True, the raw log entries will be printed on the console instead of sending to a flume source. Enable this ONLY on a development setup.
print_raw_log = False
log_directory = None
node_name=None
rotation_interval = None # if rotation_interval == -1, the server won't rotate it's log.
hdfs_raw_log_dir = None
hadoop_command = None

from local_settings import *

assert node_name is not None
assert log_directory is not None
assert rotation_interval is not None
assert hdfs_raw_log_dir is not None
assert hadoop_command is not None
