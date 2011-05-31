#!/usr/bin/env python
import sys
import mongo_client


site_id, site_name = sys.argv[1], sys.argv[2]

mongo_client.updateSite(site_id, site_name)

