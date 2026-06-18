"""测试 go_back"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.app_lifecycle import LaunchAndWait
from tools.interaction import TapByName
from tools.error_handling import GoBack
from tools.device_info import WaitSeconds

wda = connect_wda()

# 打开设置
LaunchAndWait(wda).run({"bundle_id": "com.apple.Preferences"})

# 进入通用
for name in ("通用", "蓝牙"):
    r = TapByName(wda).run({"name": name})
    if "✅" in r.text:
        break
WaitSeconds(wda).run({"seconds": 1.5})



# 返回
print(GoBack(wda).run({}).text)



wda.delete_session()
