def getSiteDBName(site_id):
    return "tjbsite_%s" % site_id

def getSiteDBCollection(connection, site_id, collection_name):
    return connection[getSiteDBName(site_id)][collection_name]

def getSiteDB(connection, site_id):
    return connection[getSiteDBName(site_id)]


def sign(float):
    if float > 0:
        return 1
    elif float == 0:
        return 0
    else:
        return -1


def updateCollectionRecord(collection, key_name, key_value, initial_dict, content_dict):
    record_in_db = collection.find_one({key_name: key_value})
    if record_in_db is None:
        record_in_db = initial_dict
    record_in_db.update(content_dict)
    collection.save(record_in_db)


class UploadItemSimilarities:
    def __init__(self, connection, site_id, type="V"):
        self.connection = connection
        self.last_item1 = None
        self.last_rows = []
        self.item_similarities = getSiteDBCollection(self.connection, site_id, 
                        "item_similarities_%s" % type)

    def updateSimOneRow(self):
        item_in_db = self.item_similarities.find_one({"item_id": self.last_item1})
        if item_in_db is None:
            item_in_db = {}
        item_in_db.update({"item_id": self.last_item1, "mostSimilarItems": self.last_rows})
        self.item_similarities.save(item_in_db)
        self.last_item1 = self.item_id1
        self.last_rows = []

    def __call__(self, item_similarities_file_path):
        for line in open(item_similarities_file_path, "r"):
            self.item_id1, item_id2, similarity = line.split(",")
            similarity = float(similarity)
            if self.last_item1 is None:
                self.last_item1 = self.item_id1
                last_rows = []
            elif self.last_item1 != self.item_id1:
                self.updateSimOneRow()
            self.last_rows.append((item_id2, similarity))

        if len(self.last_rows) != 0:
            self.updateSimOneRow()


def convertSecondsAsHoursMinutesSeconds(seconds):
    seconds = int(seconds)
    hours = seconds / 3600
    a = seconds % 3600
    minutes = a / 60
    seconds_remain = a % 60
    result_str = ""
    if hours > 0:
        result_str += "%s hours " % hours
    if minutes > 0:
        result_str += "%s minutes " % minutes
    result_str += "%s seconds" % seconds_remain
    return result_str

