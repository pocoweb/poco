import hashlib


def doHash(id):
    return hashlib.md5(id).hexdigest()

