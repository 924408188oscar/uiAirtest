# -*- encoding=utf8 -*-


# generate html report
# from airtest.report.report import simple_report
# simple_report(__file__, logpath=True)
# -*- encoding=utf8 -*-
__author__ = "Bill"
__version__ = "1.3.0(20220810)"

import re, time, os, json, shutil
from os.path import dirname, join, abspath
from pprint import pprint
from airtest.core.api import *
from airtest.cli.parser import cli_setup
from airtest.report.report import LogToHtml
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from poco.exceptions import PocoTargetTimeout, PocoNoSuchNodeException
from airtest.core.error import AdbShellError

# =============以下为测试配置================
# Airtest Settings
package = "com.vivalnk.sdk.vSDK.demo"
activity = "com.vivalnk.sdk.demo.vital.ui.WelcomeActivity"
basedir = abspath(join(dirname(__file__), ".."))
action_interval = 0.8
retry_limit = 5

# Test Settings
target_sn = "ECGRec_202142/C860265"
target_ecgMult = [1, 2, 4]
target_accFreq = [5, 10, 25, 50, 125, 250]
target_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]
target_cases = None
# target_cases用于指定cases list，值为None时，由default_cases_generator枚举
# 如：target_cases = [(1,5,"LiveMode","RTSMode"), (1,5,"RTSMode","LiveMode")]
# 或：target_cases = None
# 其中每个case的四元组参数合法值范围请参考下方的Test Constants

ctrl_interrupt_if_log_collect_failed = False
ctrl_skip_log_collect_if_passed = True

# Test Constants
allow_totalMult = 250
allow_ecgMult = [1, 2, 4]
allow_accFreq = [5, 10, 25, 50, 125, 250]
allow_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]

default_cases_generator = ((i, j, k1, k2) for i in target_ecgMult for j in target_accFreq for k1 in target_dataMode for
                           k2 in target_dataMode if i * j <= allow_totalMult if
                           not ((i != 1 or j != 5) and (k1 == "DualMode" or k2 == "DualMode")) if k1 != k2 if
                           k2 != "NoneMode" if
                           not (j != 5 and (k1 == "RTSMode_SavePower" or k2 == "RTSMode_SavePower")))

print(target_cases)

# Test Constants
# allow_totalMult = 250
# allow_ecgMult = [1,2,4]
# allow_accFreq = [5,10,25,50,125,250]
# allow_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]
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


def start_app(package, activity):
    wake()
    log("start_app")
    shell(f"am start -n {package}/{activity}")


def input_text(poco, txt: str, ok=True):
    txt = str(txt)
    poco("android.widget.EditText").wait(timeout=10).set_text(txt)
    log(f"Input:{txt}")
    if ok:
        poco(text="Ok").click()


def scroll_find(poco, text, direction="DOWN", retry_limit=10):
    target = poco(text=text)
    is_found = False
    for i in range(retry_limit):
        with poco.freeze() as fpoco:
            if fpoco(text=text):
                is_found = True
                break
            if direction == "UP":
                poco.swipe((0.03, 0.5), direction=(0, 0.5), duration=0.5)
                sleep(1)
            elif direction == "DOWN":
                poco.swipe((0.03, 0.5), direction=(0, -0.5), duration=0.5)
                sleep(1)
            else:
                raise ValueError("Direction should be in (\"UP\", \"DOWN\")")
    if is_found:
        return target
    else:
        raise PocoNoSuchNodeException(target)


def singleton_poco():
    global global_poco
    if global_poco is None:
        global_poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False,
                                              action_interval=action_interval, pre_action_wait_for_appearance=10)
    return global_poco


def bootstrap(expname=True):
    if expname != True:
        logdir = os.path.join(basedir, "logs", expname)
    else:
        logdir = True
    auto_setup(basedir=basedir, logdir=logdir)
    poco = singleton_poco()
    return poco


def fprint(obj, file):
    if isinstance(obj, str):
        print(obj)
        print(obj, file=file)
    else:
        pprint(obj, width=150)
        pprint(obj, width=150, stream=file)


def teardown():
    try:
        shell("ps -Af|grep @|grep minicap|awk '{print $2}'|xargs kill -2")
    except:
        pass
    try:
        shell("ps -Af|grep app_process|grep rotationwatcher|awk '{print $2}'|xargs kill -2")
    except:
        pass
    sleep(20)


def parse(raw: str, pattern: str) -> str:
    matches = re.search(pattern, raw)
    if matches is None:
        return None
    target = matches.groups()[0]
    return target


def parse_op_data_dict(data_raw: str) -> dict:
    data_str = parse(data_raw, r": data = (\{.+\})")
    data_d = json.loads(data_str)
    return data_d


def parse_opLog_dict(raw_log: str) -> dict:
    pattern_c = r"(\w+): onComplete(: data = \{.+\})?"
    pattern_e = r"(\w+): onError: code = (\d+), msg = (.+)"
    matches_c = re.search(pattern_c, raw_log)
    matches_e = re.search(pattern_e, raw_log)
    job_d = dict()
    if matches_c is not None:
        groups = matches_c.groups()
        job_d["name"] = groups[0]
        job_d["status"] = "onComplete"
        job_d["data"] = None if groups[1] is None else parse_op_data_dict(groups[1])
    elif matches_e is not None:
        groups = matches_e.groups()
        job_d["name"] = groups[0]
        job_d["status"] = "onError"
        job_d["code"] = int(groups[1])
        job_d["msg"] = groups[2]
    else:
        raise NotImplementedError("Unknown Job Log Format")
    return job_d


def parse_panel_dict(poco, entry: str) -> dict:
    poco(text=entry).click()
    wait_for_if_progress(poco, 1, 3)
    wait_for_panel(poco)
    item_d = dict()
    with poco.freeze() as fpoco:
        items = fpoco(nameMatches=f"{package}:id/tv.+")
        for item in items:
            kv_split = item.get_text().split(':')
            k, v = kv_split[0].strip(), kv_split[1].strip()
            item_d[k] = v
        fpoco(text="Ok").click()
        sleep(1)
    return item_d


def wait_for_if_progress(poco, max_loop=1, first_timeout=10, loop_timeout=5):
    ctx = poco("android:id/progress").sibling("android:id/message")
    for i in range(max_loop):
        try:
            timeout = first_timeout if i == 0 else loop_timeout
            is_appeared = False
            ctx.wait_for_appearance(timeout=timeout)
            log(f"【{ctx.get_text()}】")
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


def wait_for_panel(poco):
    ctx = poco(f"{package}:id/parentPanel")
    ctx.wait_for_appearance(timeout=20)


def wait_for_if_reconnect(poco):
    wait_for_if_progress(poco, 5, 10)
    ctx = poco(text="Log Detail")  # 判断是否进入设备命令页
    try:
        ctx.wait_for_appearance(timeout=5)
    except PocoTargetTimeout:
        return False
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


def start_sdk():
    sleep(10)
    start_app(package, activity)


def stop_sdk():
    sleep(3)
    stop_app(package)


def restart_sdk():
    stop_sdk()
    start_sdk()


def cmdPage_to_engPage(poco):
    '''入口：设备命令页，出口：工程模式页'''
    btn = scroll_find(poco, "Open Engineer Module", "DOWN")
    btn.click()
    poco(text="Engineering Operations").wait_for_appearance(timeout=20)


def engPage_to_cmdPage(poco):
    '''入口：工程模式页，出口：设备命令页'''
    poco("Navigate up").click()
    sleep(1)
    scroll_find(poco, "Log Detail", "UP")


def get_connected_sn(poco):
    return poco(f"{package}:id/toolbar").child("android.widget.TextView").wait(timeout=20).get_text()


def is_connected_target(poco, sn):
    connected_sn = get_connected_sn(poco)
    log(f"Connected={connected_sn}, Target={sn}")
    return connected_sn == sn


def connect_dev(poco, sn, auto_disconnect=False, auto_clear_log=False):
    restart_sdk()
    is_target = None
    if wait_for_if_reconnect(poco):
        is_target = is_connected_target(poco, sn)
        is_to_disconnect = (auto_disconnect == True) or (is_target == False)
        if is_to_disconnect:
            log(f"Disconnecting device {sn}")
            disconnect_dev(poco)
            is_target = None
    if auto_clear_log:
        stop_sdk()
        del_log_files(sn)
        clr_logcat()
        connect_dev(poco, sn, auto_disconnect, False)
        return
    log(f"Connecting device {sn}")
    if is_target is None:
        poco(text="Device Scanning").wait_for_appearance(timeout=20)
        is_scan_by_sn = scan_check_if_sn(poco, sn)
        assert_equal(is_scan_by_sn, True, "R: connect_dev()")
    else:
        log(f"R: connect_dev() skipped, {sn} connected and auto_disconnect set to False")


def disconnect_dev(poco):
    btn = scroll_find(poco, "Disconnect", "DOWN")
    btn.click()
    wait_for_if_progress(poco)
    sleep(1)


def assert_cmdEcho(log_d: dict, expect_status: str, test_point: str):
    status = log_d["status"]
    if status != expect_status:
        assert_equal(False, True, test_point)


def clr_opLog(poco):
    poco(text="Log Detail").click()
    poco(text="Operation Log").click()
    clr_btn = poco(text="Clear")
    clr_btn.wait_for_appearance(timeout=10)
    clr_btn.click()


def get_clr_opLog(poco, log_id=-1) -> dict:
    poco(text="Log Detail").click()
    poco(text="Operation Log").click()
    poco(text="Clear").wait_for_appearance(timeout=10)
    with poco.freeze() as fpoco:
        raw = fpoco("android.widget.ListView").children()[log_id].get_text()
        fpoco(text="Clear").click()
    log_d = parse_opLog_dict(raw)
    return log_d


def clr_dataLog(poco):
    poco(text="Log Detail").click()
    poco(text="Data Log").click()
    clr_btn = poco(text="Clear")
    clr_btn.wait_for_appearance(timeout=10)
    clr_btn.click()


def get_clr_dataLog_poco(poco, log_id=-1):
    poco(text="Log Detail").click()
    poco(text="Data Log").click()
    poco(text="Clear").wait_for_appearance(timeout=10)
    sleep(1)
    ret = None
    with poco.freeze() as fpoco:
        lv = fpoco("android.widget.ListView")
        if lv.exists():
            for lv_i in lv.children():
                if len(lv_i.get_text().strip()) > 0:
                    ret = lv_i
        fpoco(text="Clear").click()
    return ret


def check_dataLog_if_exist(poco, curr_dataMode):
    is_ck = True
    clr_dataLog(poco)
    wait_time = 2 if curr_dataMode != "LiveMode" else 30
    sleep(wait_time)
    ret = get_clr_dataLog_poco(poco)
    if ret is None:
        is_ck = False
    return is_ck


def get_sn(poco):
    poco(text="Read SN").click()
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run get_sn()")
    return log_d["data"]["sn"]


def set_get_patchClock(poco):
    poco(text="SetClock").click()
    ts_a = int(shell("date +%s"))  # Android Timestamp
    log_d = get_clr_opLog(poco)
    if log_d["status"] == "onComplete":
        ts_b = log_d["data"]["time"]  # Patch Timestamp
        return ts_a, int(ts_b / 1000)
    elif log_d["status"] == "onError":
        return None, None


def get_patchVersion_dict(poco) -> dict:
    poco(text="Read Patch Version").click()
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run get_patchVersion()")
    ret = log_d["data"]
    return ret


def get_deviceInfo_dict(poco) -> dict:
    poco(text="Read Device Info").click()
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run get_deviceInfo()")
    ret = log_d["data"]
    return ret


def get_patchStatus_dict(poco) -> dict:
    ret_d = parse_panel_dict(poco, "Check Patch Status")
    return ret_d


def get_patchSelfTest_dict(poco) -> dict:
    ret_d = parse_panel_dict(poco, "Self-Test")
    return ret_d


def get_batteryVolt_from_selfTest(poco):
    patchSelfTest = get_patchSelfTest_dict(poco)
    try:
        batteryVolt = patchSelfTest["Battery Voltage"]
        return batteryVolt
    except:
        return None


def get_batteryVolt_from_patchStatus(poco):
    patchStatus = get_patchStatus_dict(poco)
    try:
        batteryVolt = patchStatus["Battery Voltage"]
        return batteryVolt
    except:
        return None


def clr_flash(poco):
    poco(text="Erase Flash").click()


def get_patchFirmware(poco) -> str:
    patchVersion = get_patchVersion_dict(poco)
    try:
        global patchFirmware
        patchFirmware = patchVersion["fwVersion"]
        return patchFirmware
    except:
        return None


def check_patchSelfTest_if_ok(poco):
    return get_batteryVolt_from_selfTest(poco) is not None


def check_patchStatus_if_ok(poco):
    return get_batteryVolt_from_patchStatus(poco) is not None


def check_patchVersion_if_ok(poco):
    return get_patchFirmware(poco) is not None


def get_lead_sample_bool(poco):
    patchStatus = get_patchStatus_dict(poco)
    lead_text = patchStatus["LeadOn"]
    sample_text = patchStatus["Sampling"]
    lead = True if lead_text == "Yes" else False
    sample = True if sample_text == "Yes" else False
    return lead, sample


def set_sample_bool(poco, new_sample):
    if new_sample == True:
        poco(text="Start Sampling").click()
    else:
        poco(text="Stop Sampling").click()
    wait_for_if_progress(poco, 1, 3)
    log_d = get_clr_opLog(poco)


def get_accLeadoff_accMain_bool(poco):
    patchStatus = get_patchStatus_dict(poco)
    accLeadoff_text = patchStatus["LeadOffAccEnable"]
    accMain_text = patchStatus["AccSamplingEnable"]
    accLeadoff = True if accLeadoff_text == "Yes" else False
    accMain = True if accMain_text == "Yes" else False
    return (accLeadoff, accMain)


def set_accLeadoff_bool(poco, new_accLeadoff: bool):
    btn = scroll_find(poco, "LeadOffAccSampling", "DOWN")
    btn.click()
    if new_accLeadoff == True:
        poco(text="Enable").click()
    else:
        poco(text="Disable").click()
    if wait_for_if_progress(poco, 5, 10):
        return True
    else:
        scroll_find(poco, "Log Detail", "UP")
        return False


def set_accMain_bool(poco, new_accMain: bool):
    btn = scroll_find(poco, "enable/disable acc sampling", "DOWN")
    btn.click()
    if new_accMain == True:
        poco(text="Enable").click()
    else:
        poco(text="Disable").click()
    if wait_for_if_progress(poco, 5, 10):
        return True
    else:
        scroll_find(poco, "Log Detail", "UP")
        return False


def get_dataSwitch(poco) -> list:
    patchStatus = get_patchStatus_dict(poco)
    RTS_str = patchStatus["RTS Channel Enable"]
    FlashStream_str = patchStatus["Flash Channel Enable"]
    RTSSaveInFlash_str = patchStatus["RTS Save to Flash"]
    RTS = True if RTS_str == "Yes" else False
    FlashStream = True if FlashStream_str == "Yes" else False
    RTSSaveInFlash = True if RTSSaveInFlash_str == "Yes" else False
    return [RTS, FlashStream, RTSSaveInFlash]


def get_dataMode(poco):
    patchStatus = get_patchStatus_dict(poco)
    dataMode = patchStatus["Data Stream Mode"]
    if dataMode == "None":
        dataMode = "NoneMode"
    return dataMode


def set_dataMode(poco, new_mode):
    if new_mode in allow_dataMode:
        poco(text="Switch Data Stream Mode").click()
        poco(text=new_mode).click()
        wait_for_if_progress(poco, 5, 3)
    else:
        raise ValueError("Unsupported DataMode")


def get_userInfo(poco):
    poco(text="Read Info").click()
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run get_userInfo()")
    raw = log_d["data"]["userInfo"].strip("\x00")
    return raw


def set_userInfo(poco, userInfo):
    poco(text="Set Info").click()
    input_text(poco, userInfo)
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run set_userInfo()")


def clr_userInfo(poco):
    poco(text="Erase Info").click()
    log_d = get_clr_opLog(poco)
    assert_cmdEcho(log_d, "onComplete", "I: Run clr_userInfo()")


def set_accFreq(poco, curr_ecgMult, curr_accMain, accFreq):
    cmdPage_to_engPage(poco)
    btn = scroll_find(poco, "Write Acc Frequency", "DOWN")
    btn.click()
    real_accFreq = accFreq * curr_ecgMult
    input_text(poco, real_accFreq)
    if wait_for_if_progress(poco, 5):
        pass
    else:
        engPage_to_cmdPage(poco)


def set_ecgMult(poco, curr_accFreq, ecgMult):
    cmdPage_to_engPage(poco)
    btn = scroll_find(poco, "写入采样倍数", "DOWN")
    btn.click()
    input_text(poco, ecgMult)
    if wait_for_if_progress(poco, 5):
        pass
    else:
        engPage_to_cmdPage(poco)


def get_accFreq(poco, curr_ecgMult):
    patchStatus = get_patchStatus_dict(poco)
    real_accFreq = int(patchStatus["ACC Frequency"])
    accFreq = int(real_accFreq / curr_ecgMult)
    return accFreq


def get_ecgMult(poco):
    patchStatus = get_patchStatus_dict(poco)
    ecgFreq = int(patchStatus["ECG Frequency"])
    ecgMult = int(ecgFreq / 128)
    return ecgMult


def prepare_log_collect_dir():
    if "airtest" in shell(f"ls {dev_log_root}/"):
        shell(f"rm -rf {log_collect_dir}")
    shell(f"mkdir {log_collect_dir}")


def save_log_files_to_dir(sn, save_dir_name, local_export_dir):
    save_dir = f"{log_collect_dir}/{save_dir_name}"
    sn = sn[-14:].replace('/', '_')
    if save_dir_name in shell(f"ls {log_collect_dir}/"):
        shell(f"rm -rf {save_dir}")
    shell(f"mkdir {save_dir}")
    if len(shell(f"ls {dev_log_root}/vSDK/{sn}/")) > 0:
        shell(f"mv {dev_log_root}/vSDK/{sn}/* {save_dir}/")
    if len(shell(f"ls {raw_log_root}/")) > 0:
        shell(f"mv {raw_log_root}/* {save_dir}/")
    shell(f"logcat -d -f {save_dir}/logcat.txt")
    device().adb.pull(save_dir, local_export_dir)


def del_log_files(sn):
    sn = sn[-14:].replace('/', '_')
    if sn in shell(f"ls {dev_log_root}/vSDK/"):
        shell(f"rm -rf {dev_log_root}/vSDK/{sn}")
        shell(f"mkdir {dev_log_root}/vSDK/{sn}")
    if len(shell(f"ls {raw_log_root}/")) > 0:
        shell(f"rm -rf {raw_log_root}/*")


def clr_logcat():
    shell('logcat -c')


###################################
def reset_patch(poco, sn):
    c_ecgMult = get_ecgMult(poco)
    set_accFreq(poco, c_ecgMult, True, 5)
    set_ecgMult(poco, 5, 1)
    set_accMain_bool(poco, True)
    set_accLeadoff_bool(poco, False)
    clr_flash(poco)
    set_dataMode(poco, "FullDualMode")
    sleep(1)
    log("Patch Reset Done!")


def test_get_sn(poco, sn):
    assert_equal(get_sn(poco), sn[-14:], "R: get_sn()")


def test_set_get_patchClock(poco):
    lead, sample = get_lead_sample_bool(poco)
    ts_a, ts_b = set_get_patchClock(poco)
    turned_sample_for_test = False
    if lead == True and sample == True:
        assert_equal(ts_a, None, "R: set_get_patchClock() Lead On&Sample On")
        set_sample_bool(poco, False)
        turned_sample_for_test = True
        ts_a, ts_b = set_get_patchClock(poco)
    time_delta = ts_a - ts_b
    is_ok = abs(time_delta) <= 10
    log(f"Clock[Android, Patch]={[ts_a, ts_b]}")
    if turned_sample_for_test:
        assert_equal(is_ok, True, "A: set_get_patchClock() Lead On&Sample Off")
        set_sample_bool(poco, sample)
    else:
        assert_equal(is_ok, True, "R: set_get_patchClock() Lead Off/Sample Off")


def test_set_accLeadoff_accMain(poco, curr_accFreq):
    if curr_accFreq == 5:
        v_select = [(True, True), (True, False), (False, False), (False, True)]
        v_expect = v_select
        v_real = []
        for t in v_select:
            set_accLeadoff_bool(poco, t[0])
            set_accMain_bool(poco, t[1])
            result = get_accLeadoff_accMain_bool(poco)
            v_real.append(result)
        assert_equal(v_real, v_expect, f"R: set_accLeadoff_accMain()")
    else:
        v_select = [True, False]
        v_expect = v_select
        v_real = []
        log("R: set_accMain() skipped, accFreq is not 5")
        for t in v_select:
            set_accLeadoff_bool(poco, t)
            result, _ = get_accLeadoff_accMain_bool(poco)
            v_real.append(result)
        assert_equal(v_real, v_expect, f"R: set_accLeadoff()")


def test_set_get_clr_userInfo(poco):
    v_input = ["vivalink"]
    i_input = ["123456789012345???????"]
    v_expect = []
    i_expect = []
    v_real = []
    i_real = []
    for t in v_input:
        set_userInfo(poco, t)
        real = get_userInfo(poco)
        v_expect.append(t)
        v_real.append(real)
        clr_userInfo(poco)
        real = get_userInfo(poco)
        v_expect.append("")
        v_real.append(real)
    assert_equal(v_real, v_expect, f"R: set_get_clr_userInfo() Vaild")
    for t in i_input:
        set_userInfo(poco, t)
        real = get_userInfo(poco)
        i_expect.append(t[:15])
        i_real.append(real)
        clr_userInfo(poco)
        real = get_userInfo(poco)
        i_expect.append("")
        i_real.append(real)
    assert_equal(i_real, i_expect, "R: set_get_clr_userInfo() Invaild")


def test_check_patchSelfTest_if_ok(poco):
    v_expect = True
    clr_opLog(poco)
    v_real = check_patchSelfTest_if_ok(poco)
    assert_equal(v_real, v_expect, "R: check_patchSelfTest_if_ok()")


def test_check_patchStatus_if_ok(poco):
    v_expect = []
    v_real = []
    clr_opLog(poco)
    for i in range(5):
        v_expect.append(True)
        result = check_patchStatus_if_ok(poco)
        v_real.append(result)
    assert_equal(v_real, v_expect, "R: check_patchStatus_if_ok()")


def test_check_patchVersion_if_ok(poco):
    v_expect = True
    clr_opLog(poco)
    v_real = check_patchVersion_if_ok(poco)
    assert_equal(v_real, v_expect, "R: check_patchVersion_if_ok()")


def test_check_dataSwitch_if_match(poco, curr_dataMode):
    v_expect = allow_dataSwitch_T[curr_dataMode]
    v_real = get_dataSwitch(poco)
    for i, v in enumerate(v_expect):
        if v is None:
            v_real[i] = None
    assert_equal(v_real, v_expect, "R: check_dataSwitch_if_match()")


def test_check_dataLog_if_exist(poco, curr_dataMode):
    # Precondition: lead on and start sampling
    lead, sample = get_lead_sample_bool(poco)
    if lead == True and sample == True:
        v_expect = True
        v_real = check_dataLog_if_exist(poco, curr_dataMode)
        assert_equal(v_real, v_expect, "R: check_dataLog_if_exist()")
    else:
        log("R: check_dataLog_if_exist() skipped, patch is lead off")


def test_set_check_sample_if_ok(poco, curr_dataMode):
    # Precondiction: lead on
    v_select = [False, True]
    v_expect = [(False, False), (True, curr_dataMode != "NoneMode")]
    v_real = []
    lead, _ = get_lead_sample_bool(poco)
    set_dataMode(poco, curr_dataMode)
    if lead == True:
        for t in v_select:
            set_sample_bool(poco, t)
            _, is_sample = get_lead_sample_bool(poco)
            clr_dataLog(poco)
            is_dataLog = check_dataLog_if_exist(poco, curr_dataMode)
            v_real.append((is_sample, is_dataLog))
        assert_equal(v_real, v_expect, "R: set_check_sample_if_ok()")
    else:
        log("R: set_check_sample_if_ok() skipped, patch is lead off")


def test_set_accFreq_param(poco, c_ecgMult, c_accMain, t_accFreq):
    v_expect = t_accFreq
    set_accFreq(poco, c_ecgMult, c_accMain, t_accFreq)
    v_real = get_accFreq(poco, c_ecgMult)
    assert_equal(v_real, v_expect, f"R: set_accFreq_param({t_accFreq})")


def test_set_ecgMult_param(poco, c_accFreq, t_ecgMult):
    v_expect = t_ecgMult
    set_ecgMult(poco, c_accFreq, t_ecgMult)
    v_real = get_ecgMult(poco)
    assert_equal(v_real, v_expect, f"R: set_ecgMult_param({t_ecgMult})")


def test_set_fromMode_param(poco, t_dataMode):
    v_expect = t_dataMode
    set_dataMode(poco, t_dataMode)
    v_real = get_dataMode(poco)
    assert_equal(v_real, v_expect, f"R: set_fromMode_param({t_dataMode})")


def test_set_toMode_param(poco, t_dataMode):
    v_expect = t_dataMode
    set_dataMode(poco, t_dataMode)
    v_real = get_dataMode(poco)
    assert_equal(v_real, v_expect, f"R: set_toMode_param({t_dataMode})")


def reset_for_full_test(sn):
    poco = bootstrap()
    wake()
    stop_sdk()
    prepare_log_collect_dir()
    connect_dev(poco, sn, False, False)
    reset_patch(poco, sn)


def full_test_with_ecgMult_accFreq_fromMode_toMode(sn, target_cases):
    if target_cases is None:
        log("Cases List is not assigned, Run default_cases_generator!")
        v_select = list(default_cases_generator)
    else:
        log("Cases List is assigned by user!")
        v_select = target_cases

    # init status
    c_ecgMult = 1
    c_accFreq = 5
    c_dataMode = "FullDualMode"

    cnt_total = len(v_select)
    cnt_passed = 0
    v_failed = []
    start_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    export_root = prepare_export_struct(start_time)
    prepare_logs_dir()
    log(f"Cases Count={cnt_total}")
    log(f"Cases List={str(v_select)}")

    for i, v in enumerate(v_select):
        last_e = None
        # unpack the params
        t_ecgMult = v[0]
        t_accFreq = v[1]
        t_fromMode = v[2]
        t_toMode = v[3]
        # build the strings
        expname = f"{t_ecgMult}-{t_accFreq}-{t_fromMode}-{t_toMode}"
        savedir = f"[{expname}]-[{start_time}]"
        progress_str = f"[{i + 1}/{cnt_total}]"
        params_str = f"[ecgMult={t_ecgMult}, accFreq={t_accFreq}, From={t_fromMode}, To={t_toMode}]"

        # Startup Stage
        is_start_ok = False
        try_i = 0
        while not is_start_ok:
            try:
                poco = bootstrap(expname)
                log(f"{progress_str} Case Begin: {params_str}")
                connect_dev(poco, sn, True, True)
                is_start_ok = True
            except Exception as e:
                snapshot(msg="Breakpoint Snapshot")
                log(e)
                if try_i > retry_limit:  # 重试retry_limit次后仍失败，直接failed
                    last_e = type(e)
                    log("Exception at Startup excceed retry_limit, Failed!")
                    break
                else:
                    log(f"Exception at Startup, retry #{try_i + 1}!")
                    try_i += 1
                    sleep(10)

        # Test Stage
        is_test_ok = False
        try:
            if is_start_ok:
                # setting params
                c_accLeadoff, c_accMain = get_accLeadoff_accMain_bool(poco)
                c_ecgMult = get_ecgMult(poco)
                test_set_accFreq_param(poco, c_ecgMult, c_accMain, t_accFreq)
                c_accFreq = t_accFreq
                test_set_ecgMult_param(poco, c_accFreq, t_ecgMult)
                c_ecgMult = t_ecgMult
                test_set_fromMode_param(poco, t_fromMode)
                c_dataMode = t_fromMode

                # tests before switch data mode
                test_check_patchVersion_if_ok(poco)
                test_check_patchSelfTest_if_ok(poco)
                test_check_patchStatus_if_ok(poco)
                test_check_dataSwitch_if_match(poco, c_dataMode)
                # switch data mode
                test_set_toMode_param(poco, t_toMode)
                c_dataMode = t_toMode
                # tests after switch data mode
                test_check_patchVersion_if_ok(poco)
                test_check_patchSelfTest_if_ok(poco)
                test_check_patchStatus_if_ok(poco)
                test_check_dataSwitch_if_match(poco, c_dataMode)
                test_get_sn(poco, sn)
                test_set_get_patchClock(poco)
                test_set_get_clr_userInfo(poco)
                test_set_accLeadoff_accMain(poco, c_accFreq)
                test_set_check_sample_if_ok(poco, c_dataMode)

                is_test_ok = True
        except Exception as e:
            snapshot(msg="Breakpoint Snapshot")
            log(e)
            last_e = type(e)
        finally:
            # generate html report
            if is_start_ok and is_test_ok:
                cnt_passed += 1
                log(f"Passed at {params_str}")
                savedir = "P-" + savedir
                export_dir = join(export_root, "pass", expname)
            else:
                log(f"Failed at {params_str}")
                savedir = "F-" + savedir
                export_dir = join(export_root, "fail", expname)
                v_failed.append((v, str(last_e)))
            log_dir = join(basedir, "logs", expname)
            log_builder = LogToHtml(script_root=__file__, log_root=log_dir, export_dir=export_dir, lang="zh",
                                    plugins=["poco.utils.airtest.report"])
            log_builder.report()

        # Collect Stage
        stop_sdk()
        teardown()
        if is_start_ok and is_test_ok and ctrl_skip_log_collect_if_passed:
            log("Case is Passed, Collect Stage Skipped!")
            log(f"{progress_str} Case End!")
        else:
            is_collect_ok = False
            try_i = 0
            while not is_collect_ok:
                try:
                    # 先尝试保存SDK日志到设备存储，再尝试adb pull到export_dir
                    save_log_files_to_dir(sn, savedir, export_dir)
                    log(f"{progress_str} Case End!")
                    is_collect_ok = True
                except Exception as e:
                    log(e)
                    if try_i > retry_limit:
                        if ctrl_interrupt_if_log_collect_failed:
                            log("Exception at Collect excceed retry_limit, Interrupted!")
                            raise
                        else:
                            log("Exception at Collect excceed retry_limit, Ignored!")
                            break
                    else:
                        log(f"Exception at Collect, retry #{try_i + 1}!")
                        try_i += 1
                        sleep(10)

    # Generate result.txt
    end_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    with open(join(export_root, "result.txt"), "w") as f:
        fprint("#######TEST RESULT#######", file=f)
        fprint(f"Start Time: {start_time}", file=f)
        fprint(f"End Time: {end_time}", file=f)
        fprint(f"Patch SN: {sn}", file=f)
        fprint(f"Patch FW: {patchFirmware}", file=f)
        fprint(f"Total: {cnt_total}, Passed: {cnt_passed}", file=f)
        if cnt_passed == cnt_total:
            fprint("Result: All Passed!", file=f)
        else:
            cnt_f = len(v_failed)
            fprint(f"Result: Failed {cnt_f} Cases!", file=f)
            fprint("At:", file=f)
            fprint(v_failed, file=f)


if __name__ == "__main__":
    reset_for_full_test(target_sn)
    full_test_with_ecgMult_accFreq_fromMode_toMode(target_sn, target_cases)
