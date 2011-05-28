hbase_thrift_host = "localhost"
hbase_thrift_port = 9090
hdfs_item_similarity_root_path = None
tmp_dir = None
hadoop_command = None

from local_settings import *

assert hdfs_item_similarity_root_path is not None
assert tmp_dir is not None
assert hadoop_command is not None
