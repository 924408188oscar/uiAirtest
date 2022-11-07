import time

from airtest.core.api import *


def start_sdk(package, activity):
    sleep(10)
    start_app(package, activity)


def stop_sdk(package):
    sleep(3)
    stop_app(package)


def restart_sdk(package, activity):
    stop_app(package)
    time.sleep(5)
    start_app(package)
    # start_app(package, activity)
