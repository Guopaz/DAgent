"""测试 get_tab_bar"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base import connect_wda
from tools.interaction import GetTabBar
from tools.device_info import WaitSeconds

wda = connect_wda()

tool = GetTabBar(wda)

# 场景 1: 主屏幕（通常无 TabBar）
# print("=== 场景 1: 主屏幕（预期无 TabBar） ===")
# r = tool.run({"action": "list"})
# print(r.text)

# # 场景 2: 先打开一个有 TabBar 的 App，测试 list 和 switch
# print("\n=== 场景 2: 打开测试 App ===")
# # 尝试打开一个可能的 App
# test_apps = [
#     ("店长直聘", "com.kanzun.shopzp"),
#     ("健康", "com.apple.Health"),
#     ("时钟", "com.apple.mobiletimer"),
# ]
# opened = False
# for name, bid in test_apps:
#     r = TapByName(wda).run({"name": name})
#     if "✅" in r.text:
#         WaitSeconds(wda).run({"seconds": 3})
#         opened = True
#         break

# if not opened:
#     print("⚠️ 未找到测试 App，尝试用设置 App")
#     from tools.app_lifecycle import LaunchAndWait
#     LaunchAndWait(wda).run({"bundle_id": "com.apple.Preferences"})

# 列出 Tab
print("\n=== 场景 3: get_tab_bar(action='list') ===")
r = tool.run({"action": "list"})
print(r.text)

# 如果找到 TabBar，尝试切换
data = r.data
if data.get("found") and data.get("tab_count", 0) > 0:
    target = min(data["tab_count"] - 1, 1)  # 切换到第二个 Tab（避免和当前重复）
    if target != data.get("selected_index"):
        print(f"\n=== 场景 4: switch to index={target} ===")
        r = tool.run({"action": "switch", "index": target})
        print(r.text)

    print(f"\n=== 场景 5: switch with tab_name ===")
    first_tab = data["tabs"][0]
    name = first_tab.get("label") or first_tab.get("name", "")
    if name:
        r = tool.run({"action": "switch", "tab_name": name})
        print(r.text)

# 场景 6: 参数冲突
print("\n=== 场景 6: 同时提供 index 和 tab_name（应报错） ===")
r = tool.run({"action": "switch", "index": 0, "tab_name": "xxx"})
print(r.text)

# 场景 7: index 越界
print("\n=== 场景 7: index 越界 ===")
r = tool.run({"action": "switch", "index": 999})
print(r.text)

# 场景 8: 不存在的 tab_name
print("\n=== 场景 8: 不存在的 tab_name ===")
r = tool.run({"action": "switch", "tab_name": "__不存在__"})
print(r.text)

wda.delete_session()
