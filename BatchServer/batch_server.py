import logging
import sys
sys.path.append("../")
import time
import os
import os.path
import settings
from ApiServer import mongo_client


# TODO: use hamake?

sys.path.insert(0, "../")

logging.basicConfig(format="%(asctime)s|%(levelname)s|%(name)s|%(message)s",
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %I:%M:%S")

logger = logging.getLogger("Batch Server")


class ShellExecutionError(Exception):
    pass

class BaseFlow:
    def __init__(self, name):
        self.name = name
        self.logger = logging.getLogger()
        self.jobs = []
        self.dependencies = []

    def dependOn(self, flow):
        self.parent = flow
        flow.dependencies.append(self)

    def __call__(self):
        for job_callable in self.jobs:
            if not self._execJob(job_callable):
                return False
        # execute downlines
        for dependency in self.dependencies:
            dependency()
        return True

    def _exec_shell(self, command):
        logger.info("Execute %s" % command)
        ret_code = os.system(command)
        if ret_code != 0:
            raise ShellExecutionError("Shell Execution Failed, ret_code=%s" % ret_code)

    def _execJob(self, callable):
        try:
            logger.info("About to Start Job: %s" % callable)
            callable()
            logger.info("Job: %s succeeds." % callable)
            return True
        except:
            logger.critical("An Exception happened while running Job: %s" % callable,
                exc_info=True)
            # TODO: mark failed status in database and send message (email, sms)
            return False


class PreprocessingFlow(BaseFlow):
    def __init__(self):
        BaseFlow.__init__(self, "preprocessing")
        self.work_dir = settings.work_dir
        self.jobs += [self.do_backfill,
                      self.do_reverse_reversed_backfilled_raw_logs]

    def do_backfill(self):
        from preprocessing import backfiller
        last_ts = None # FIXME: load correct last_ts from somewhere
        bf = backfiller.BackFiller(SITE_ID, last_ts, 
                    os.path.join(settings.work_dir, "reversed_backfilled_raw_logs"))
        last_ts = bf.start() # FIXME: save last_ts somewhere 

    def do_reverse_reversed_backfilled_raw_logs(self):
        input_path  = os.path.join(settings.work_dir, "reversed_backfilled_raw_logs")
        output_path = os.path.join(settings.work_dir, "backfilled_raw_logs")
        self._exec_shell("%s <%s >%s" % (settings.tac_command, input_path, output_path))


class BaseSimilarityCalcFlow(BaseFlow):
    def __init__(self, type):
        BaseFlow.__init__(self, "similarities-calc:%s" % type)
        self.type = type
        self.work_dir = os.path.join(settings.work_dir, "item_similarities_%s" % type)
        if not os.path.isdir(self.work_dir):
            os.mkdir(self.work_dir)
        self.jobs += self.getExtractUserItemMatrixJobs() + [self.do_sort_user_item_matrix,
                      self.do_emit_cooccurances,
                      self.do_sort_cooccurances,
                      self.do_count_cooccurances,
                      self.do_format_item_similarities,
                      self.do_make_item_similarities_bi_directional,
                      self.do_sort_item_similarities_bi_directional,
                      self.do_extract_top_n,
                      self.do_upload_item_similarities_result]


    def do_sort_user_item_matrix(self):
        input_path  = os.path.join(self.work_dir, "user_item_matrix")
        output_path = os.path.join(self.work_dir, "user_item_matrix_sorted")
        self._exec_shell("sort %s > %s" % (input_path, output_path))


    def do_emit_cooccurances(self):
        from similarity_calculation.amazon.emit_cooccurances import emit_cooccurances
        input_path  = os.path.join(self.work_dir, "user_item_matrix_sorted")
        output_path = os.path.join(self.work_dir, "cooccurances_not_sorted")
        emit_cooccurances(input_path, output_path)


    def do_sort_cooccurances(self):
        input_path  = os.path.join(self.work_dir, "cooccurances_not_sorted")
        output_path = os.path.join(self.work_dir, "cooccurances_sorted")
        self._exec_shell("sort %s > %s" % (input_path, output_path))


    def do_count_cooccurances(self):
        input_path  = os.path.join(self.work_dir, "cooccurances_sorted")
        output_path = os.path.join(self.work_dir, "item_similarities_raw")
        self._exec_shell("uniq -c %s > %s" % (input_path, output_path))


    def do_format_item_similarities(self):
        from similarity_calculation.amazon.format_item_similarities import format_item_similarities
        input_path  = os.path.join(self.work_dir, "item_similarities_raw")
        output_path = os.path.join(self.work_dir, "item_similarities_formatted")
        format_item_similarities(input_path, output_path)


    def do_make_item_similarities_bi_directional(self):
        from similarity_calculation.make_similarities_bidirectional import make_similarities_bidirectional
        input_path  = os.path.join(self.work_dir, "item_similarities_formatted")
        output_path = os.path.join(self.work_dir, "item_similarities_bi_directional")
        make_similarities_bidirectional(input_path, output_path)


    def do_sort_item_similarities_bi_directional(self):
        input_path  = os.path.join(self.work_dir, "item_similarities_bi_directional")
        output_path = os.path.join(self.work_dir, "item_similarities_bi_directional_sorted")
        self._exec_shell("sort %s > %s" % (input_path, output_path))


    def do_extract_top_n(self):
        from similarity_calculation.extract_top_n import extract_top_n
        input_path  = os.path.join(self.work_dir, "item_similarities_bi_directional_sorted")
        output_path = os.path.join(self.work_dir, "item_similarities_top_n")
        n = 20
        extract_top_n(input_path, output_path, n)


    def do_upload_item_similarities_result(self):
        from common.utils import UploadItemSimilarities
        import pymongo
        input_path = os.path.join(self.work_dir, "item_similarities_top_n")
        connection = pymongo.Connection()
        uis = UploadItemSimilarities(connection, SITE_ID, self.type)
        uis(input_path)


class VSimiliarityCalcFlow(BaseSimilarityCalcFlow):
    def __init__(self):
        BaseSimilarityCalcFlow.__init__(self, "V")

    def getExtractUserItemMatrixJobs(self):
        return [self.do_extract_user_item_matrix,
                self.do_de_duplicate_user_item_matrix]

    def do_extract_user_item_matrix(self):
        from preprocessing.extract_user_item_matrix import v_extract_user_item_matrix
        input_path  = os.path.join(self.parent.work_dir, "backfilled_raw_logs")
        output_path = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        v_extract_user_item_matrix(input_path, output_path)

    def do_de_duplicate_user_item_matrix(self):
        input_path  = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        output_path = os.path.join(self.work_dir, "user_item_matrix")
        self._exec_shell("sort < %s | uniq > %s" % (input_path, output_path))


class PLOSimilarityCalcFlow(BaseSimilarityCalcFlow):
    def __init__(self):
        BaseSimilarityCalcFlow.__init__(self, "PLO")

    def getExtractUserItemMatrixJobs(self):
        return [self.do_extract_user_item_matrix,
                self.do_de_duplicate_user_item_matrix]

    def do_extract_user_item_matrix(self):
        from preprocessing.extract_user_item_matrix import plo_extract_user_item_matrix
        input_path  = os.path.join(self.parent.work_dir, "backfilled_raw_logs")
        output_path = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        plo_extract_user_item_matrix(input_path, output_path)

    def do_de_duplicate_user_item_matrix(self):
        input_path  = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        output_path = os.path.join(self.work_dir, "user_item_matrix")
        self._exec_shell("sort < %s | uniq > %s" % (input_path, output_path))


class BuyTogetherSimilarityFlow(BaseSimilarityCalcFlow):
    def __init__(self):
        BaseSimilarityCalcFlow.__init__(self, "BuyTogether")

    def getExtractUserItemMatrixJobs(self):
        return [self.do_extract_user_item_matrix,
                self.do_de_duplicate_user_item_matrix]

    def do_extract_user_item_matrix(self):
        from preprocessing.extract_user_item_matrix import buytogether_extract_user_item_matrix
        input_path  = os.path.join(self.parent.work_dir, "backfilled_raw_logs")
        output_path = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        buytogether_extract_user_item_matrix(input_path, output_path)

    def do_de_duplicate_user_item_matrix(self):
        input_path  = os.path.join(self.work_dir, "user_item_matrix_maybe_dup")
        output_path = os.path.join(self.work_dir, "user_item_matrix")
        self._exec_shell("sort < %s | uniq > %s" % (input_path, output_path))


class ViewedUltimatelyBuyFlow(BaseFlow):
    def __init__(self):
        BaseFlow.__init__(self, "preprocessing")
        self.work_dir = os.path.join(settings.work_dir, "viewed_ultimately_buy")
        if not os.path.isdir(self.work_dir):
            os.mkdir(self.work_dir)
        self.jobs += [self.do_extract_user_view_buy_logs,
                      self.do_sort_user_view_buy_logs,
                      self.do_pair_view_buy,
                      self.count_pairs,
                      self.count_item_view,
                      self.upload_viewed_ultimately_buy]

    def do_extract_user_view_buy_logs(self):
        from viewed_ultimately_buy.extract_user_view_buy_logs import extract_user_view_buy_logs
        input_path  = os.path.join(self.parent.work_dir, "backfilled_raw_logs")
        output_path = os.path.join(self.work_dir, "user_view_buy_logs")
        extract_user_view_buy_logs(input_path, output_path)

    def do_sort_user_view_buy_logs(self):
        input_path  = os.path.join(self.work_dir, "user_view_buy_logs")
        output_path = os.path.join(self.work_dir, "user_view_buy_logs_sorted")
        self._exec_shell("sort <%s >%s" % (input_path, output_path))

    def do_pair_view_buy(self):
        from viewed_ultimately_buy.pair_view_buy import pair_view_buy
        input_path  = os.path.join(self.work_dir, "user_view_buy_logs_sorted")
        output_path = os.path.join(self.work_dir, "view_buy_pairs")
        pair_view_buy(input_path, output_path)

    def count_pairs(self):
        input_path  = os.path.join(self.work_dir, "view_buy_pairs")
        output_path = os.path.join(self.work_dir, "view_buy_pairs_counted")
        self._exec_shell("sort <%s | uniq -c >%s" % (input_path, output_path))

    def count_item_view(self):
        #FIXME a hack
        input_path = os.path.join(settings.work_dir, "item_similarities_V", "user_item_matrix")
        output_path = os.path.join(self.work_dir, "item_view_times")
        self._exec_shell("cut -d , -f 2 <%s | sort | uniq -c >%s" % (input_path, output_path))

    def upload_viewed_ultimately_buy(self):
        from viewed_ultimately_buy.upload_viewed_ultimately_buy import upload_viewed_ultimately_buy
        item_view_times_path = os.path.join(self.work_dir, "item_view_times")
        view_buy_pairs_counted_path = os.path.join(self.work_dir, "view_buy_pairs_counted")
        upload_viewed_ultimately_buy(SITE_ID, item_view_times_path, view_buy_pairs_counted_path)

class BeginFlow(BaseFlow):
    def __init__(self):
        BaseFlow.__init__(self, "Root")
        self.jobs += [self.begin]

    def begin(self):
        self.logger.info("Start Work on %s", SITE_ID)

class FinishFlow(BaseFlow):
    def __init__(self):
        BaseFlow.__init__(self, "Root")
        self.jobs += [self.finish]

    def finish(self):
        #TODO: set last finished work flag in database
        logger.info("Finish Work on %s", SITE_ID)

# TODO: removed items' similarities should also be removed.

begin_flow = BeginFlow()

preprocessing_flow = PreprocessingFlow()
preprocessing_flow.dependOn(begin_flow)

v_similarity_calc_flow = VSimiliarityCalcFlow()
v_similarity_calc_flow.dependOn(preprocessing_flow)

plo_similarity_calc_flow = PLOSimilarityCalcFlow()
plo_similarity_calc_flow.dependOn(preprocessing_flow)


buy_together_similarity_flow = BuyTogetherSimilarityFlow()
buy_together_similarity_flow.dependOn(preprocessing_flow)


viewed_ultimately_buy_flow = ViewedUltimatelyBuyFlow()
viewed_ultimately_buy_flow.dependOn(preprocessing_flow)


#finish_flow = FinishFlow()
#finish_flow.dependOn(similarity_calc_flow)

# TODO: mark success/failure state


if __name__ == "__main__":
    while True:
        for site in mongo_client.loadSites():
            now = time.time()
            if site.get("last_update_ts") is None \
                or now - site.get("last_update_ts") > site["calc_interval"]:
                SITE_ID = site["site_id"]
                try:
                    begin_flow()
                finally:
                    logger.info("====================================")
                #FIXME: save last_update_ts
        sleep_seconds = 10
        logger.info("Go to sleep for %s seconds." % sleep_seconds)
        time.sleep(sleep_seconds)
