import os

from configT.ConnectionManagement import connect_dev
from configT.common import scan_check_if_sn
from configT.ecgMode import full_test_with_ecgMult_accFreq_fromMode_toMode
from configT.generator_cases import generator_case

print("adb devices: ")
print(os.system("adb devices"))
print("adb packages: ")
print(os.system("adb shell pm list package -3"))
print("env: ")
print(os.environ)
from airtest.core.api import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco

auto_setup(__file__)
app_package = "com.vivalnk.sdk.vSDK.demo"
app_activity = "com.vivalnk.sdk.demo.vital.ui.WelcomeActivity"
action_interval = 0.8


class TestApp(object):
    poco = None

    @classmethod
    def setup_class(cls):
        print("setup_class")
        cls.poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False,
                                           action_interval=action_interval, pre_action_wait_for_appearance=10)

    # def __init__(self):
    #     self.poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False,
    #                                         action_interval=action_interval, pre_action_wait_for_appearance=10)
    @staticmethod
    def get_poco():
        poco = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False,
                                       action_interval=action_interval, pre_action_wait_for_appearance=10)
        return poco

    @classmethod
    def teardown_class(cls):
        print("teardown_class")

    # cls.poco.stop_running()

    def setup_method(self):
        log(f"clear app data")
        clear_app(app_package)
        print("启动app")
        # wake()
        # time.sleep(0.3)
        start_app(app_package, app_activity)
        # start_app(app_package)
        print("点击进入")

    def teardown_method(self, method):
        print("停止app")
        # stop_app(app_package)

    def test_clear_appData(self):
        clear_app(app_package)

    def test_sdk(self):
        # self.setup_method()
        # wake()
        # time.sleep(0.3)
        # start_app(app_package)
        # shell(f"am start -n {app_package}/{app_activity}")
        time.sleep(3)
        print("test start")
        target_sn = "ECGRec_202142/C860265"
        print(target_sn)
        # scan_check_if_sn(self.poco, target_sn)
        connect_dev(self.poco, target_sn, False, False)
        time.sleep(3)
        start_btn = self.poco(text="Check Patch Status")
        start_btn.click()
        time.sleep(6)
        start_btn = self.poco(text="OK")
        start_btn.click()
        time.sleep(3)
        log(f"{target_sn} Switch Data Stream Mode")
        start_btn = self.poco(text="Switch Data Stream Mode")
        start_btn.click()

    def test_full_test_with_ecgMult_accFreq_fromMode_toMode(self):
        target_sn = "ECGRec_202142/C860265"
        connect_dev(self.poco, target_sn, False, False)
        default_cases_generator = generator_case()
        full_test_with_ecgMult_accFreq_fromMode_toMode(target_sn, default_cases_generator)
