"""测试 inspect_element"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.perception import InspectElement

wda = connect_wda()

# 先看屏幕拿到一个元素名
src = wda.get_source()
import re
m = re.search(r'label="([^"]+)"', src)
name = m.group(1) if m else "设置"
print(f"目标元素: '{name}'")

tool = InspectElement(wda)
print(tool.run({"name": name}).text)

wda.delete_session()
