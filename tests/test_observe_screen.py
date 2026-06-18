"""测试 observe_screen"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.perception import ObserveScreen

wda = connect_wda()
tool = ObserveScreen(wda)

print("\n=== XML 模式 ===")
print(tool.run({"mode": "xml"}).text[:500])

print("\n=== 截图模式 ===")
r = tool.run({"mode": "screenshot"})
print(r.text[:200] if r.text else "无数据")

wda.delete_session()
