import urllib


_abbr_map = {"vi_": {"action_name": 'V',
                     "full_name": 'viewItem',
                     "index": 1,
                    "i": "item_id",
                    "u": "user_id"},
              "af_": {"action_name": 'AF',
                      "full_name": 'addFavorite',
                      "index": 2,
                     "i": "item_id",
                     "u": "user_id"},
              "rf_": {"action_name": 'RF',
                      "full_name": "removeFavorite",
                      "index": 3,
                     "i": "item_id",
                     "u": "user_id"
                    },
              "ri_": {"action_name": 'RI',
                      "full_name": "rateItem",
                      "index": 4,
                     "i": "item_id",
                     "s": "score",
                     "u": "user_id"
                    },
              "asc": {"action_name": 'ASC',
                      "full_name": "addOrderItem",
                      "index": 5,
                     "u": "user_id",
                     "i": "item_id"
                    },
              "rsc": {"action_name": 'RSC',
                      "full_name": "removeOrderItem",
                      "index": 6,
                      "u": "user_id",
                      "i": "item_id"
                    },
              "plo": {"action_name": 'PLO',
                      "full_name": "placeOrder",
                      "index": 7,
                      "u": "user_id",
                      "o": "order_content"
                    },
              "upi": {"action_name": 'UItem',
                      "full_name": "updateItem",
                      "index": 8,
                     "i": "item_id",
                     "l": "item_link",
                     "n": "item_name",
                     "d": "description",
                     "m": "image_link",
                     "p": "price",
                     "r": "market_price",
                     "c": "categories"
                    },
               "rmi": {"action_name": 'RItem',
                      "full_name": "removeItem",
                      "index": 8,
                      "i": "item_id"
                   },
               "rcv": {"action_name": 'RecVAV',
                       "full_name": 'getAlsoViewed',
                       "index": 9,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
               "rcb": {"action_name": 'RecBAB',
                       "full_name": "getAlsoBought",
                       "index": 10,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rct": {"action_name": 'RecBTG',
                        "full_name": "getBoughtTogether",
                        "index": 11,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rcu": {"action_name": 'RecVUB',
                        "full_name": "getUltimatelyBought",
                        "index": 12,
                       "u": "user_id",
                       "i": "item_id",
                       "c": "include_item_info",
                       "a": "amount"
                   },
                "rch": {"action_name": 'RecBOBH',
                        "full_name": "getByBrowsingHistory",
                        "index": 13,
                      "u": "user_id",
                      "h": "browsing_history",
                      "c": "include_item_info",
                      "a": "amount"
                   },
                "rcp": {"action_name": "RecPH",
                        "full_name": "getByPurchasingHistory",
                        "index": 14,
                        "u": "user_id",
                        "c": "include_item_info",
                        "a": "amount"},
                #"rcc": {"action_name": "RecSC",
                #        "full_name": "getByShoppingCart",
                #        "index": 15,
                #        "u": "user_id",
                #        "c": "include_item_info",
                #        "a": "amount"}
             }

def generateALL_ATTR_NAMES_js():
    global _abbr_map
    attr_names = {}
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            if len(attr_abbr) < 2:
                attr_names[_abbr_map[request_type][attr_abbr]] = 1

    result = "ALL_ATTR_NAMES = {\n"
    for attr_name in attr_names.keys():
        result += "    '%s': 1,\n" % (attr_name)
    result += "}\n"

    return result


def generateFULL_NAME_ATTR_NAME2FULL_ABBR_NAME_js():
    result = "FULL_NAME_ATTR_NAME2FULL_ABBR_NAME = {\n"
    global _abbr_map
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            if len(attr_abbr) < 2:
                result += '    "' + _abbr_map[request_type]["full_name"] + ":" + _abbr_map[request_type][attr_abbr] + '" : "' + request_type + attr_abbr + '",\n'
    result += "}\n"
    return result

def generateFULL_NAME2MASK_js():
    result = "FULL_NAME2MASK = {\n"
    global _abbr_map
    for request_type in _abbr_map.keys():
        index = _abbr_map[request_type]["index"]
        result += '    "' + _abbr_map[request_type]["full_name"] + '" : ' + str(2 ** (index - 1)) + ',\n'
    result += "}\n"
    return result


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


def createActionName2FullName():
    global _abbr_map
    result = {}
    for request_type in _abbr_map.keys():
        for attr_abbr in _abbr_map[request_type].keys():
            result[_abbr_map[request_type]["action_name"]] = _abbr_map[request_type]["full_name"]
    return result

ACTION_NAME2FULL_NAME = createActionName2FullName()


class PackedRequest:
    def __init__(self):
        self.shared_params = {}
        self.requests = []

    def addSharedParams(self, param_name, param_value):
        self.shared_params[param_name] = param_value

    def addRequest(self, action_name, request):
        self.requests.append((action_name, request))

    def getUrlArgs(self, api_key):
        url_args = {"api_key": api_key}
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
        return url_args

    def getFullUrl(self, api_key, api_prefix):
        url_args = self.getUrlArgs(api_key)
        return api_prefix + "/1.0/packedRequest?" + urllib.urlencode(url_args)


if __name__ == "__main__":
    pr = PackedRequest()
    #pr.addSharedParams("user_id", "U335")
    #pr.addSharedParams("item_id", "I318")
    #pr.addSharedParams("include_item_info", "yes")
    pr.addRequest("UItem", {"item_id": 35, "item_link": "http://example.com/item?id=35", "item_name": "Something"})
    #pr.addRequest("RI", {"score": 5})
    #pr.addRequest("RecBTG", {"amount": 8})
    #pr.addRequest("RecBOBH", {"amount": 5, "browsing_history": "I122,I133,I155"})
    print pr.getFullUrl("demo1", "http://localhost:5588")
