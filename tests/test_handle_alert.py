"""测试 handle_alert"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.error_handling import HandleAlert

wda = connect_wda()

tool = HandleAlert(wda)
print(tool.run({"action": "accept"}).text)
print(tool.run({"action": "dismiss"}).text)
print(tool.run({"action": "custom", "button_name": "允许"}).text)

wda.delete_session()
