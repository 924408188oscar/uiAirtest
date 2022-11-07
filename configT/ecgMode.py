from airtest.core.api import *
import re, time, os, json, shutil
from os.path import dirname, join, abspath
from pprint import pprint
from airtest.core.api import *
from airtest.cli.parser import cli_setup
from airtest.report.report import LogToHtml
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from poco.exceptions import PocoTargetTimeout, PocoNoSuchNodeException

from configT.ConnectionManagement import *
from configT.config import *
from configT.generator_cases import generator_case
from testcase.sdk import get_clr_opLog, assert_cmdEcho, engPage_to_cmdPage, cmdPage_to_engPage, test_set_fromMode_param, \
    test_check_patchVersion_if_ok, test_check_patchSelfTest_if_ok, test_check_patchStatus_if_ok, \
    test_check_dataSwitch_if_match, test_set_toMode_param, test_get_sn, test_set_get_patchClock, \
    test_set_get_clr_userInfo, test_set_accLeadoff_accMain, test_set_check_sample_if_ok

package = "com.vivalnk.sdk.vSDK.demo"
activity = "com.vivalnk.sdk.demo.vital.ui.WelcomeActivity"
basedir = abspath(join(dirname(__file__), ".."))
action_interval = 0.8
retry_limit = 5




def prepare_export_struct(start_time: str) -> str:
    export_root = join(basedir, f"export_{start_time}")
    os.makedirs(join(export_root, "pass"))
    os.makedirs(join(export_root, "fail"))
    return export_root


def prepare_logs_dir():
    logs_dir = join(basedir, "logs")
    if os.path.exists(logs_dir):
        shutil.rmtree(logs_dir)
    os.makedirs(logs_dir)


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


def wait_for_panel(poco):
    ctx = poco(f"{package}:id/parentPanel")
    ctx.wait_for_appearance(timeout=20)


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


def get_patchStatus_dict(poco) -> dict:
    ret_d = parse_panel_dict(poco, "Check Patch Status")
    return ret_d


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


allow_dataMode = ["NoneMode", "DualMode", "LiveMode", "FullDualMode", "RTSMode", "RTSMode_SavePower"]


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


def input_text(poco, txt: str, ok=True):
    txt = str(txt)
    poco("android.widget.EditText").wait(timeout=10).set_text(txt)
    log(f"Input:{txt}")
    if ok:
        poco(text="Ok").click()


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
