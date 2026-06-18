"""测试 check_app_status"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.app_lifecycle import CheckAppStatus

wda = connect_wda()

tool = CheckAppStatus(wda)
print(tool.run({"bundle_id": "com.apple.Preferences"}).text)
print(tool.run({"bundle_id": "com.does.not.exist"}).text)

wda.delete_session()
