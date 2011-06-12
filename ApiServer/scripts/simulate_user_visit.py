import sys
import urllib2
import urllib
import simplejson as json


site_id = sys.argv[1]
file_name = sys.argv[2]
max_count = int(sys.argv[3])


SERVER_NAME = "127.0.0.1"
SERVER_PORT = 5588


def api_access(path, params, tuijianbaoid=None, as_json=True):
    url = "http://%s:%s%s?%s" % (SERVER_NAME, SERVER_PORT, path, 
                    urllib.urlencode(params))
    req = urllib2.Request(url)
    if tuijianbaoid <> None:
        req.add_header("Cookie", "tuijianbaoid=%s" % tuijianbaoid)
    result = urllib2.urlopen(req).read()
    if as_json:
        result_obj = json.loads(result)
        return result_obj
    else:
        return result

count = 0
for line in open(file_name, "r"):
    count += 1
    if count % 5000 == 0:
        print count / float(max_count) * 100
    if count > max_count:
        break
    user_id, tjbid, item_id = line.strip().split(",")
    result = api_access("/tui/viewItem", 
            {"site_id": site_id, "item_id": item_id,
             "user_id": user_id},
             tuijianbaoid=tjbid)
    assert result["code"] == 0, repr(result)

