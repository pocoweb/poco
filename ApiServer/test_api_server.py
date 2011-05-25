import urllib
import os
import os.path
import settings
import simplejson as json
import hashlib
import time


def api_access(path, params, as_json=True):
    url = "http://%s:%s%s?%s" % (settings.server_name, settings.server_port, path, 
                    urllib.urlencode(params))
    result = urllib.urlopen(url).read()
    if as_json:
        result_obj = json.loads(result)
        return result_obj
    else:
        return result


def generate_uid():
    return hashlib.md5(repr(time.time())).hexdigest()


def getCurrentFilePath(site_id):
    return os.path.join(settings.log_directory, site_id, "current")


#def removeCurrentFile(site_id):
#    file_path = os.path.join(settings.log_directory, site_id, "current")
#    if os.path.isfile(file_path):
#        os.remove(file_path)


def readCurrentFileLines(site_id):
    return open(getCurrentFilePath(site_id), "r").readlines()


def getLastLineSplitted(site_id):
    lines = readCurrentFileLines(site_id)
    return lines[-1].strip().split(",")


SITE_ID = "tester"

def assertEquals(a, b):
    assert a == b, "Assert failed, %s != %s" % (a, b)


def assertNotEquals(a, b):
    assert a != b, "Assert failed, %s == %s" % (a, b)


def test_viewItem1():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/viewItem",
        {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id, 
         "session_id": session_id})
    assertEquals(result, {"code": 0})
    assertEquals(getLastLineSplitted(SITE_ID)[1:], ["V", user_id, session_id, item_id])

def test_viewItem2():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/viewItem",
        {"site_id": SITE_ID, "item_id": item_id, "user_id": user_id, 
         "session_id": session_id, "callback": "blah"},
         as_json=False)
    assertEquals(result, "blah({\"code\": 0})")
    assertEquals(getLastLineSplitted(SITE_ID)[1:], ["V", user_id, session_id, item_id])


def test_viewItemSiteIdNotExists():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/viewItem",
        {"site_id": "THESITEWHICHNOTEXISTS", "item_id": item_id, "user_id": user_id, 
         "session_id": session_id, "callback": "blah"},
         as_json=False)
    assertEquals(result, "blah({\"code\": 2})")
    assertNotEquals(getLastLineSplitted(SITE_ID)[1:], ["V", user_id, session_id, item_id])


def test_addFavorite():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/addFavorite",
        {"site_id": SITE_ID, "user_id": user_id, "session_id": session_id,
         "item_id": item_id})
    assertEquals(result,{"code": 0})
    assertEquals(getLastLineSplitted(SITE_ID)[1:], ["AF", user_id, session_id, item_id])


def test_removeFavorite():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/removeFavorite",
        {"site_id": SITE_ID, "user_id": user_id, "session_id": session_id,
         "item_id": item_id})
    assertEquals(result,{"code": 0})
    assertEquals(getLastLineSplitted(SITE_ID)[1:], ["RF", user_id, session_id, item_id])


def test_rateItem():
    item_id, user_id, session_id = generate_uid(), generate_uid(), generate_uid()
    result = api_access("/action/rateItem",
        {"site_id": SITE_ID, "user_id": user_id, "session_id": session_id,
         "item_id": item_id, "score": "5"})
    assertEquals(result,{"code": 0})
    assertEquals(getLastLineSplitted(SITE_ID)[1:], ["RI", user_id, session_id, item_id, "5"])


def test_updateItem():
    print "TODO: Update Item Test"


def test_removeItem():
    print "TODO: Remove Item Test"


def test_recommendViewedAlsoView():
    print "TODO: test_recommendViewedAlsoView"


def test_RecommendBasedOnBrowsingHistory():
    print "TODO: RecommendBasedOnBrowsingHistory"


if __name__ == "__main__":
    test_viewItem1()
    test_viewItem2()
    test_viewItemSiteIdNotExists()
    test_addFavorite()
    test_removeFavorite()
    test_rateItem()
    test_updateItem()
    test_removeItem()
    test_recommendViewedAlsoView()
    test_RecommendBasedOnBrowsingHistory()
