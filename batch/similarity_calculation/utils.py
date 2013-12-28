

TMP_DIR = "tmp"
def reset_and_enter_tmp_dir():
    if os.path.is_dir(TMP_DIR):
        os.system("rm -rf %s" % TMP_DIR # FIXME: use a safer way
    os.chdir(TMP_DIR)

