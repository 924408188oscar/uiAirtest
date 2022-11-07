import configT.config
from airtest.core.api import *

dev_log_root = configT.config.dev_log_root
raw_log_root = configT.config.raw_log_root


def del_log_files(sn):
    sn = sn[-14:].replace('/', '_')
    if sn in shell(f"ls {dev_log_root}/vSDK/"):
        shell(f"rm -rf {dev_log_root}/vSDK/{sn}")
        shell(f"mkdir {dev_log_root}/vSDK/{sn}")
    if len(shell(f"ls {raw_log_root}/")) > 0:
        shell(f"rm -rf {raw_log_root}/*")


def clr_logcat():
    shell('logcat -c')
