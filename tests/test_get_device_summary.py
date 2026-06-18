"""测试 get_device_summary"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.device_info import GetDeviceSummary

wda = connect_wda()

tool = GetDeviceSummary(wda)
print(tool.run({}).text)

wda.delete_session()
