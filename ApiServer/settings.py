server_name = "localhost"
server_port = 5588
log_directory = None # You have to specify it in local_settings.py
rotation_interval = None
#rotation_size_limit = None

from local_settings import *

assert log_directory <> None 
assert rotation_interval <> None
#assert rotation_size_limit <> None
