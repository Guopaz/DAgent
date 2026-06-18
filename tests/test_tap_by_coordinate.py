"""测试 tap_by_coordinate"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import TapByCoordinate

wda = connect_wda()

size = wda.get_window_size()
cx, cy = int(size["width"] / 2), int(size["height"] / 2)

tool = TapByCoordinate(wda)
print(tool.run({"x": cx, "y": cy}).text)
print(tool.run({"x": 0, "y": 0}).text)

wda.delete_session()
