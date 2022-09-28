
# if __name__ == '__main__':
#     print_hi('PyCharm')

from datetime import datetime

import pytest


if __name__ == '__main__':
    date_str = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    # 测试报告的名称
    report_name = date_str + "sdk.html"

    pytest.main([f"--html={report_name}"])
    # pytest.main([f"--s -q -l --html={report_name} --self-contained-html"])

