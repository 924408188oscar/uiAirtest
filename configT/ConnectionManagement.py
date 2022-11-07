from poco.exceptions import *

import configT.config
from configT.delLogFile import *
from configT.sdkOperation import *
from airtest.core.api import *

package = configT.config.package
activity = configT.config.activity


def scan_check_if_sn(poco, sn):
    '''入口：扫描列表页，出口：设备命令页（找到设备）/扫描列表页（未找到设备）'''
    print("'''入口：扫描列表页，出口：设备命令页（找到设备）/扫描列表页（未找到设备）'''")
    start_btn = poco(text="Scan")
    stop_btn = poco(text="Stop Scanning")
    print(stop_btn.exists())
    # if stop_btn.exists():
    #     while stop_btn.exists():
    #         stop_btn.click()
    #         stop_btn.refresh()
    #     sleep(1)
    #     start_btn.click()
    #     start_btn.refresh()
    sleep(10)
    stop_btn.click()
    sleep(6)
    with poco.freeze() as fpoco:
        if fpoco(text=sn):
            print("connect.............")
            fpoco(text=sn).click()
            wait_for_if_progress(poco)
            return True
        else:
            return False


def wait_for_if_reconnect(poco):
    wait_for_if_progress(poco, 5, 10)
    ctx = poco(text="Log Detail")  # 判断是否进入设备命令页
    try:
        ctx.wait_for_appearance(timeout=5)
    except PocoTargetTimeout:
        return False
    return True


def get_connected_sn(poco):
    print(poco(f"{package}:id/toolbar").child("android.widget.TextView").wait(timeout=20).get_text())
    return poco(f"{package}:id/toolbar").child("android.widget.TextView").wait(timeout=20).get_text()


def is_connected_target(poco, sn):
    connected_sn = get_connected_sn(poco)
    log(f"Connected={connected_sn}, Target={sn}")
    return connected_sn == sn


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


def connect_dev(poco, sn, auto_disconnect=False, auto_clear_log=False):
    print(package, activity)
    restart_sdk(package, activity)
    is_target = None
    if wait_for_if_reconnect(poco):
        is_target = is_connected_target(poco, sn)
        is_to_disconnect = (auto_disconnect == True) or (is_target == False)
        if is_to_disconnect:
            log(f"Disconnecting device {sn}")
            disconnect_dev(poco)
            is_target = None
    if auto_clear_log:
        stop_sdk(package)
        del_log_files(sn)
        clr_logcat()
        connect_dev(poco, sn, auto_disconnect, False)
        return
    log(f"Connecting device {sn}")
    print("Connecting device {sn}", is_target)
    if is_target is None:
        poco(text="Device Scanning").wait_for_appearance(timeout=20)
        is_scan_by_sn = scan_check_if_sn(poco, sn)
        assert_equal(is_scan_by_sn, True, "R: connect_dev()")
        print("22222")
    else:
        log(f"R: connect_dev() skipped, {sn} connected and auto_disconnect set to False")


def scroll_find(poco, text1, direction="DOWN", retry_limit=10):
    target = poco(text=text1)
    is_found = False
    for i in range(retry_limit):
        with poco.freeze() as fpoco:
            if fpoco(text=text1):
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


def disconnect_dev(poco):
    btn = scroll_find(poco, "Disconnect", "DOWN")
    btn.click()
    wait_for_if_progress(poco)
    sleep(1)
