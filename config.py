#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os
from common.readconfig import ReadConfig

# 项目目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 日志目录
LOG_PATH = os.path.join(BASE_DIR, 'log')

# 测试日志
AIRTEST_LOG = os.path.join(BASE_DIR, 'log', 'airtest')

# report_path
REPORT_PATH = os.path.join(BASE_DIR, "report")

apps = {
    'oscar': os.path.join(BASE_DIR, 'oscar')
}

# configT.ini
ini = {
    'oscar': ReadConfig(os.path.join(apps['oscar'], 'config.ini'))
}

# 页面数据
elements = {
    'oscar': os.path.join(BASE_DIR, 'oscar', 'element')
}

# airtest_img
airImg = {
    'oscar': os.path.join(BASE_DIR, 'oscar', 'images')
}

if __name__ == '__main__':
    print(ini['oscar'].package_name)
