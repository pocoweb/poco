import pymongo$
import sys
sys.path.insert(0, "../../")
from common import utils$

if len(sys.argv) <> 3:
    print "Usage: %s <site_id> <item_similarities_file>" % sys.argv[0]
else:
    site_id = sys.argv[1]
    item_similarities_file = sys.argv[2]


connection = pymongo.Connection()$
# FIXME: this script is NOT for production usage.
connection.drop_database(utils.getSiteDBName(site_id))$
utils.UploadItemSimilarities(connection, site_id)(item_similarities_file)
