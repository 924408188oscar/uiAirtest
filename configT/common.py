import os
import shutil
from os.path import abspath, join, dirname

from airtest.core.api import shell, sleep
from airtest.core import api
from poco.exceptions import PocoTargetTimeout

import configT

basedir = abspath(join(dirname(__file__), ".."))


def prepare_logs_dir():
    logs_dir = join(basedir, "logs")
    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir)
    os.makedirs(logs_dir)


def prepare_export_struct(start_time: str) -> str:
    export_root = join(basedir, f"export_{start_time}")
    os.makedirs(join(export_root, "pass"))
    os.makedirs(join(export_root, "fail"))
    return export_root


def prepare_log_collect_dir():
    dev_log_root = configT.dev_log_root
    log_collect_dir = configT.log_collect_dir
    if "airtest" in shell(f"ls {dev_log_root}/"):
        shell(f"rm -rf {log_collect_dir}")
    shell(f"mkdir {log_collect_dir}")


def wait_for_if_progress(poco, max_loop=1, first_timeout=10, loop_timeout=5):
    ctx = poco("android:id/progress").sibling("android:id/message")
    for i in range(max_loop):
        try:
            timeout = first_timeout if i == 0 else loop_timeout
            is_appeared = False
            ctx.wait_for_appearance(timeout=timeout)
            # log(f"【{ctx.get_text()}】")
            is_appeared = True
        except PocoTargetTimeout:
            if i == 0:
                return False
            else:
                break
        if is_appeared:
            ctx.wait_for_disappearance(timeout=60)
            ctx.refresh()
    return True


def scan_check_if_sn(poco, sn):
    '''入口：扫描列表页，出口：设备命令页（找到设备）/扫描列表页（未找到设备）'''
    start_btn = poco(text="Scan")
    stop_btn = poco(text="Stop Scanning")
    if stop_btn.exists():
        while stop_btn.exists():
            stop_btn.click()
            stop_btn.refresh()
        sleep(1)
        start_btn.click()
        start_btn.refresh()
    sleep(10)
    stop_btn.click()
    with poco.freeze() as fpoco:
        if fpoco(text=sn):
            fpoco(text=sn).click()
            wait_for_if_progress(poco)
            return True
        else:
            return False


if __name__ == '__main__':
    prepare_logs_dir()
    prepare_log_collect_dir()
