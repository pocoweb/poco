def getSiteDBName(site_id):
    return "tjbsite_%s" % site_id

def getSiteDBCollection(connection, site_id, collection_name):
    return connection[getSiteDBName(site_id)][collection_name]

class UploadItemSimilarities:
    def __init__(self, connection, site_id):
        self.connection = connection
        self.last_item1 = None
        self.last_rows = []
        self.item_similarities = getSiteDBCollection(self.connection, site_id, 
                        "item_similarities")

    def insertSimOneRow(self):
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
                self.insertSimOneRow()
            self.last_rows.append((item_id2, similarity))

        if len(self.last_rows) != 0:
            self.insertSimOneRow()
