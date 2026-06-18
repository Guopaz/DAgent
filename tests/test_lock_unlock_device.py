"""测试 lock_unlock_device"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.device_info import LockUnlockDevice, WaitSeconds

wda = connect_wda()

tool = LockUnlockDevice(wda)
print(tool.run({"action": "lock"}).text)
WaitSeconds(wda).run({"seconds": 1})
print(tool.run({"action": "unlock"}).text)

wda.delete_session()
