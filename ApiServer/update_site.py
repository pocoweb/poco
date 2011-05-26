#!/usr/bin/env python
import sys
import hbase_client


# Sites Table
# rowkey: site_id; properties: p:site_name p:site_id items:1 items:2 
hbase_client.initTable("sites")


site_id, site_name = sys.argv[1], sys.argv[2]

hbase_client.updateSite(site_id, site_name)

