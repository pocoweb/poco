'''
The algorithm in this file is adapted from org.apache.mahout.cf.taste.impl.similarity.LoglikelihoodSimilarity
'''
import math


def twoLogLambda(k1, k2, n1, n2):
    p = (k1 + k2) / (n1 + n2)
    return 2.0 * (logL(k1 / n1, k1, n1)
                  + logL(k2 / n2, k2, n2)
                  - logL(p, k1, n1)
                  - logL(p, k2, n2))


def logL(p, k, n):
    return k * safeLog(p) + (n - k) * safeLog(1.0 - p)


def safeLog(d):
    if d <= 0:
        return 0
    else:
        return math.log(d)


def read_item_prefer_count_map(item_prefer_count_path):
    result = {}
    for line in open(item_prefer_count_path, "r"):
        count, item_id = line.strip().split(" ")
        result[item_id] = float(count)
    return result


def calc_loglikelihood(cooccurances_counts_path, user_counts_path, item_prefer_count_path, output_path):
    f_output = open(output_path, "w")
    user_counts = int(open(user_counts_path, "r").read())
    item_prefer_map = read_item_prefer_count_map(item_prefer_count_path)
    if user_counts == 0:
        return
    for line in open(cooccurances_counts_path, "r"):
        item_id1, item_id2, prefer12_count = line.strip().split(",")
        prefer12_count = float(prefer12_count)
        if prefer12_count > 1:
            prefer1 = item_prefer_map[item_id1]
            prefer2 = item_prefer_map[item_id2]
            logLikelihood = twoLogLambda(prefer12_count,
                                            prefer1 - prefer12_count,
                                            prefer2,
                                            user_counts - prefer2)
            score = 1.0 - 1.0 / (1.0 + logLikelihood)
            f_output.write("%s,%s,%s\n" % (item_id1, item_id2, score))
            f_output.flush()
    f_output.close()
