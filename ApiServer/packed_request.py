import urllib


_abbr_map = {"vi_": {"action_name": 'V',
                     "index": 1,
                    "i": "item_id",
                    "u": "user_id"},
              "af_": {"action_name": 'AF',
                      "index": 2,
                     "i": "item_id",
                     "u": "user_id"},
              "rf_": {"action_name": 'RF',
                      "index": 3,
                     "i": "item_id",
                     "u": "user_id"
                    },
              "ri_": {"action_name": 'RI',
                      "index": 4,
                     "i": "item_id",
                     "s": "score",
                     "u": "user_id"
                    },
              "asc": {"action_name": 'ASC',
                      "index": 5,
                     "u": "user_id",
                     "i": "item_id"
                    },
              "rsc": {"action_name": 'RSC',
                      "index": 6,
                      "u": "user_id",
                      "i": "item_id"
                    },
              "plo": {"action_name": 'PLO',
                      "index": 7,
                      "u": "user_id",
                      "o": "order_content"
                    },
              "upi": {"action_name": 'UItem',
                      "index": 8,
                     "i": "item_id",
                     "l": "item_link",
                     "n": "item_name",
                     "d": "description",
                     "m": "image_link",
                     "p": "price",
                     "c": "categories"
                    },
               "rmi": {"action_name": 'RItem',
                      "index": 8,
                      "i": "item_id"
                   },
               "rcv": {"action_name": 'RecVAV',
                       "index": 9,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
               "rcb": {"action_name": 'RecBAB',
                       "index": 10,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rct": {"action_name": 'RecBTG',
                        "index": 11,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rcu": {"action_name": 'RecVUB',
                        "index": 12,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rch": {"action_name": 'RecBOBH',
                        "index": 13,
                      "u": "user_id",
                      "h": "browsing_history",
                      "c": "include_item_info",
                      "a": "amount"
                   }
             }


def createActionName2Mask():
    global _abbr_map
    action_name2mask = {}
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            action_name = _abbr_map[request_type]["action_name"]
            index = _abbr_map[request_type]["index"]
            mask_array = ["0"] * 16
            mask_array[-index] = "1"
            mask = int("".join(mask_array), 2)
            action_name2mask[action_name] = mask
    return action_name2mask

ACTION_NAME2MASK = createActionName2Mask()

def createMask2ActionName():
    global _abbr_map
    mask2action_name = {}
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            action_name = _abbr_map[request_type]["action_name"]
            index = _abbr_map[request_type]["index"]
            mask_array = ["0"] * 16
            mask_array[-index] = "1"
            mask = int("".join(mask_array), 2)
            mask2action_name[mask] = action_name
    return mask2action_name


MASK2ACTION_NAME = createMask2ActionName()


def createActionNameAttrName2FullAbbrName():
    global _abbr_map
    result = {}
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            result[(_abbr_map[request_type]["action_name"], _abbr_map[request_type][attr_abbr])] = request_type + attr_abbr
    return result

ACTION_NAME_ATTR_NAME2FULL_ABBR_NAME = createActionNameAttrName2FullAbbrName()
#print ACTION_NAME_ATTR_NAME2FULL_ABBR_NAME

class PackedRequest:
    def __init__(self):
        self.shared_params = {}
        self.requests = []

    def addSharedParams(self, param_name, param_value):
        self.shared_params[param_name] = param_value

    def addRequest(self, action_name, request):
        self.requests.append((action_name, request))

    def getFullUrl(self, site_id, api_prefix):
        url_args = {"site_id": site_id}
        action_mask_set = 0
        for action_name, request in self.requests:
            for key in request.keys():
                full_abbr_name = ACTION_NAME_ATTR_NAME2FULL_ABBR_NAME.get((action_name, key), None)
                if full_abbr_name is None:
                    raise Exception("wrong (action_name, key) pair: %s" % ((action_name, key),))
                else:
                    url_args[full_abbr_name] = request[key]
            action_mask_set |= ACTION_NAME2MASK[action_name]
        for key in self.shared_params.keys():
            url_args["_" + key] = self.shared_params[key]
        url_args["-"] = "%x" % action_mask_set
        return api_prefix + "/1.0/packedRequest?" + urllib.urlencode(url_args)


if __name__ == "__main__":
    pr = PackedRequest()
    pr.addSharedParams("user_id", "U335")
    pr.addSharedParams("item_id", "I318")
    pr.addSharedParams("include_item_info", "yes")
    pr.addRequest("V", {})
    pr.addRequest("RI", {"score": 5})
    pr.addRequest("RecBTG", {"amount": 8})
    pr.addRequest("RecBOBH", {"amount": 5, "browsing_history": "I122,I133,I155"})
    print pr.getFullUrl("demo1", "http://localhost:5588")
