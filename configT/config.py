# -*- encoding=utf8 -*-

# from airtest.report.report import simple_report
# simple_report(__file__, logpath=True)
# -*- encoding=utf8 -*-
__author__ = "Oscar"
__version__ = "1.3.1(20221009)"

import re, time, os, json, shutil
from os.path import dirname, join, abspath

# =============以下为测试配置================
# Airtest Settings
package = "com.vivalnk.sdk.vSDK.demo"
activity = "com.vivalnk.sdk.demo.vital.ui.WelcomeActivity"
basedir = abspath(join(dirname(__file__), ".."))
action_interval = 0.8
retry_limit = 5

# Test Settings

target_cases = None

ctrl_interrupt_if_log_collect_failed = False
ctrl_skip_log_collect_if_passed = True

# Test Constants

allow_dataSwitch_T = {
    "NoneMode": [False, False, None],
    "DualMode": [True, True, False],  # Refering Zentao Task #906
    "LiveMode": [False, True, None],  # [RTS, Flash Steam, RTSSaveInFlash]
    "FullDualMode": [True, True, True],  # True=Open, False=Close, None=N/A
    "RTSMode": [True, False, True],
    "RTSMode_SavePower": [True, False, False]
}
# =============测试配置完===================

# =============以下为脚本主体================
# Android Path
sto_root = "/storage/emulated/0"
dev_log_root = f"{sto_root}/VivaLNK"
raw_log_root = f"{sto_root}/Android/data/{package}/vitalsdk/logs"
log_collect_dir = f"{dev_log_root}/airtest"

# Android Global
global_poco = None  # Poco单例
patchFirmware = None  # 缓存Patch Firmware

if __name__ == '__main__':
    print(dev_log_root)
    print(basedir)
