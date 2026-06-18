"""测试 wait_seconds"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from tests.base import connect_wda
from tools.device_info import WaitSeconds

wda = connect_wda()

tool = WaitSeconds(wda)

start = time.time()
r = tool.run({"seconds": 1})
elapsed = time.time() - start
print(f"{r.text} (实际 {elapsed:.2f}s)")

start = time.time()
r = tool.run({"seconds": 99})  # 应被限制为 10s
elapsed = time.time() - start
print(f"{r.text} (实际 {elapsed:.2f}s)")

wda.delete_session()
