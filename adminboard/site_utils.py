import hashlib
import random


# FIXME; should also make the api_key field unique.
# site_id also need unique constraint.
def generateApiKey(connection, site_id, site_name):
    sites = connection["tjb-db"]["sites"]
    api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
    while sites.find_one({"api_key": api_key}) is not None:
        api_key = hashlib.md5("%s:%s:%s" % (site_id, site_name, random.random())).hexdigest()[3:11]
    return api_key

