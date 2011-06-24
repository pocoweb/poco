import pymongo
import settings
from site_utils import generateApiKey


connection = pymongo.Connection(settings.mongodb_host)
sites = connection["tjb-db"]["sites"]
for site in sites.find():
    if not site.has_key("api_key"):
        api_key = generateApiKey(connection, site["site_id"], site["site_name"])
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"api_key": api_key}})
    if type(site.get("calc_interval", None)) == float:
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"calc_interval": int(site["calc_interval"])}})
    if not site.has_key("disabledFlows"):
        sites.update({"site_id": site["site_id"]},
                    {"$set": {"disabledFlows": []}})
