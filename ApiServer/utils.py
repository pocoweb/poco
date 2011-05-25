import hashlib


def doHash(id):
    return hashlib.md5(id).hexdigest()

def getSiteTableName(site_id, tableType):
    return "%s_%s" % (site_id, tableType)
