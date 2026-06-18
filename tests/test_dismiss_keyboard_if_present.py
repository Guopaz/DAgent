"""测试 dismiss_keyboard_if_present"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.error_handling import DismissKeyboardIfPresent

wda = connect_wda()

tool = DismissKeyboardIfPresent(wda)
print(tool.run({}).text)

wda.delete_session()
