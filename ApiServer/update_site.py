#!/usr/bin/env python
import sys
import hbase_client


site_id, site_name = sys.argv[1], sys.argv[2]

hbase_client.updateSite(site_id, site_name)
