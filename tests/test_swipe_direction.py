"""测试 swipe_direction — 上下左右"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import SwipeDirection

wda = connect_wda()

tool = SwipeDirection(wda)
for d in ("up", "down", "left", "right"):
    print(tool.run({"direction": d}).text)

wda.delete_session()
