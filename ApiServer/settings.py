server_name = "localhost"
server_port = 5588
hbase_thrift_host = "localhost"
hbase_thrift_port = 9090
# If you set print_raw_log as True, the raw log entries will be printed on the console instead of sending to a flume source. Enable this ONLY on a development setup.
print_raw_log = False
log_directory = None
node_name=None
rotation_interval = None

from local_settings import *

assert node_name is not None
assert log_directory is not None
assert rotation_interval is not None
