import sys
import urllib2
import urllib
import simplejson as json


file_name = sys.argv[1]
site_id = sys.argv[2]

SERVER_NAME = "api.tuijianbao.net"
SERVER_PORT = 80

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


actions = []
for line in open(file_name, "r"):
    line = line.strip()
    if line == "" or line.startswith("#"):
        action = None
    else:
        action = json.loads(line.strip())
    actions.append(action)

def execute_next(amount=1):
    global next_action_no
    for j in xrange(amount):
        action_index = next_action_no - 1
        action = actions[action_index]
        if action != None:
            print next_action_no, action
            action_name = action["action"]
            if action.has_key("tuijianbaoid"):
                tuijianbaoid = action["tuijianbaoid"]
                del action["tuijianbaoid"]
            else:
                tuijianbaoid = None
            del action["action"]
            action["site_id"] = site_id
            result = api_access("/tui/%s" % action_name,
                params=action, tuijianbaoid=tuijianbaoid,
                as_json=True)
            if result["code"] != 0:
                print "RESULT:", result
        next_action_no += 1

next_action_no = 1
while True:
    print "Next Action Index:", next_action_no
    command = raw_input(">").strip()
    if command == "":
        execute_next(1)
    elif command.startswith("e"):
        execute_next(int(command[1:]))
    elif command == "all":
        execute_next(999999999)
