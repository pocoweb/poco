import hashlib
import os.path
import settings


def doHash(id):
    return hashlib.md5(id).hexdigest()

def getSiteTableName(site_id, tableType):
    return "%s_%s" % (site_id, tableType)

def getLogDirPath(site_id):
    return os.path.join(settings.log_directory, site_id)

def getLogFilePath(site_id, file_name):
    return os.path.join(self.getLogDirPath(site_id), file_name)
