"""测试 press_home_button"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.device_info import PressHomeButton

wda = connect_wda()

tool = PressHomeButton(wda)
print(tool.run({}).text)

wda.delete_session()
