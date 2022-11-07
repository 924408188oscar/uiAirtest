import base64
import os
import time

import allure
import pytest
from py._xmlgen import html
from core.aircore import *
from airtest.core.api import connect_device


@pytest.fixture(scope='session')
def d():
    device = connect_device("android:///")
    driver = AirtestPoco(device)

    yield driver
