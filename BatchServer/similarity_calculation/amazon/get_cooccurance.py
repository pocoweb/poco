last_user = None
items = []

f = open("cooccurance", "w")
def output_cooccurance(items):
    if len(items) > 800:
        print "SKIPPED-> LAST_USER:", last_user, "LEN(ITEMS):", len(items)
        return
    for i in xrange(0, len(items)):
        for j in xrange(i+1, len(items)):
            f.write("%s,%s\n" % (items[i], items[j]))
    f.flush()

count = 0
for line in open("rating_list_sorted"):
    line = line.strip()
    count += 1
    if count % 5000 == 0:
        print count / float(6185990) * 100
    user, item = line.split(',')
    if user != last_user:
        if len(items) <> 0:
            items.sort()
            output_cooccurance(items)
        items = []
        last_user = user
    items.append(int(item))

f.close()
