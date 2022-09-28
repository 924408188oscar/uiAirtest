import os

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

    @classmethod
    def teardown_class(cls):
        print("teardown_class")

    # cls.poco.stop_running()

    def setup_method(self):
        print("启动app")
        # clear_app(app_package)
        wake()
        # time.sleep(0.3)
        # start_app(app_package, app_activity)
        start_app(app_package)
        print("点击进入")

    def teardown_method(self, method):
        print("停止app")
        stop_app(app_package)

    def test_sdk(self):
        # self.setup_method()
        wake()
        # time.sleep(0.3)
        start_app(app_package)
        # shell(f"am start -n {app_package}/{app_activity}")
        time.sleep(6)
        print("test start")
