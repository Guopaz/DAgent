"""测试 launch_and_wait"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.app_lifecycle import LaunchAndWait

wda = connect_wda()

tool = LaunchAndWait(wda)

# 启动设置
print(tool.run({"bundle_id": "com.apple.Preferences"}).text)

# 启动不存在的
print(tool.run({"bundle_id": "com.does.not.exist"}).text)

wda.delete_session()
