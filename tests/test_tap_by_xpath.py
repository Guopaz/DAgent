"""测试 tap_by_xpath"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import TapByXPath

wda = connect_wda()

tool = TapByXPath(wda)
# 不存在的元素
print(tool.run({"xpath": "//XCUIElementTypeButton[@name='__ZZZ__']"}).text)
# 无效语法
print(tool.run({"xpath": "///[[["}).text)

wda.delete_session()
