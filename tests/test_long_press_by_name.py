"""测试 long_press_by_name"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import LongPressByName

wda = connect_wda()

tool = LongPressByName(wda)
# 长按不存在的元素
print(tool.run({"name": "__FAKE__"}).text)

# 长按存在元素的图标（如 Safari）
for name in ("Safari", "设置", "Settings"):
    r = tool.run({"name": name})
    print(r.text)
    if "✅" in r.text:
        break

wda.delete_session()
