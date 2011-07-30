server_name = "localhost"
server_port = 5588
mongodb_host = None
# If you set print_raw_log as True, the raw log entries will be printed on the console. 
# For debugging purpose only, enable this ONLY on a development setup.
print_raw_log = False
api_server_prefix = None
local_raw_log_file = None

from local_settings import *

assert mongodb_host is not None
assert api_server_prefix is not None
assert local_raw_log_file is not None
