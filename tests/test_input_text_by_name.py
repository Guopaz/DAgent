"""测试 input_text_by_name"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import InputTextByName, TapByName
from tools.device_info import WaitSeconds

wda = connect_wda()

# 打开设置
for name in ("设置", "Settings"):
    r = TapByName(wda).run({"name": name})
    if "✅" in r.text:
        break
WaitSeconds(wda).run({"seconds": 3})

# 在搜索框输入
tool = InputTextByName(wda)
for name in ("搜索", "Search"):
    r = tool.run({"name": name, "text": "WiFi"})
    print(r.text)
    if "✅" in r.text:
        break

wda.delete_session()
