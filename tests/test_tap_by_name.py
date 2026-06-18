"""测试 tap_by_name"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import TapByName

wda = connect_wda()

tool = TapByName(wda)

# 点击"设置"
for name in ("浏览记录", "Settings"):
    r = tool.run({"name": name})
    print(r.text)
    if "✅" in r.text:
        break

wda.delete_session()
