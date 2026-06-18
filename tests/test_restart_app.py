"""测试 restart_app"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.app_lifecycle import RestartApp

wda = connect_wda()

tool = RestartApp(wda)
print(tool.run({"bundle_id": "com.apple.Preferences"}).text)
print(tool.run({"bundle_id": "com.does.not.exist"}).text)

wda.delete_session()
