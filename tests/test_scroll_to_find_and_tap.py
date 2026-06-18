"""测试 scroll_to_find_and_tap"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import ScrollToFindAndTap, TapByName
from tools.device_info import WaitSeconds

wda = connect_wda()

# 打开设置
for name in ("设置", "Settings"):
    r = TapByName(wda).run({"name": name})
    if "✅" in r.text:
        break
WaitSeconds(wda).run({"seconds": 3})

tool = ScrollToFindAndTap(wda)
for target in ("通用", "General", "Wi-Fi"):
    r = tool.run({"name": target, "max_scrolls": 5})
    print(r.text)
    if "✅" in r.text:
        break

wda.delete_session()
