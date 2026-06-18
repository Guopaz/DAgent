"""测试 clear_interrupt"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.error_handling import ClearInterrupt

wda = connect_wda()

tool = ClearInterrupt(wda)
print(tool.run({}).text)

wda.delete_session()
