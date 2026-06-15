"""
WDA 工具直接调用示例 - 展示如何不通过 Agent 直接使用 WDA 工具

运行方式:
  cd DAgent/examples
  python example_wda_tools.py

前置条件:
  1. iPhone 已连接到电脑并信任
  2. WebDriverAgent 已在 iPhone 上运行
  3. 已执行 iproxy 8100 8100 端口转发
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wda_client import WDAClient

def main():
    print("🔧 WDA 工具直接调用示例\n")
    
    # 1. 创建 WDA 客户端
    print("📱 连接 WDA...")
    wda = WDAClient("http://localhost:8100")
    
    # 2. 获取设备状态
    print("\n=== 设备状态 ===")
    try:
        status = wda.get_status()
        print(f"   WDA 状态: {status}")
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return
    
    # 3. 创建会话
    print("\n=== 创建会话 ===")
    session_id = wda.create_session()
    print(f"   Session ID: {session_id}")
    
    # 4. 获取屏幕信息
    print("\n=== 屏幕信息 ===")
    screen_info = wda.get_screen_info()
    print(f"   {screen_info}")
    
    # 5. 获取设备信息
    print("\n=== 设备信息 ===")
    device_info = wda.get_device_info()
    print(f"   {device_info}")
    
    # 6. 获取电池信息
    print("\n=== 电池信息 ===")
    battery_info = wda.get_battery_info()
    print(f"   {battery_info}")
    
    # 7. 获取屏幕方向
    print("\n=== 屏幕方向 ===")
    orientation = wda.get_orientation()
    print(f"   当前方向: {orientation}")
    
    # 8. 截图
    print("\n=== 截图 ===")
    screenshot = wda.get_screenshot()
    if screenshot:
        print(f"   截图大小: {len(screenshot)} bytes (base64)")
    else:
        print("   ❌ 截图失败")
    
    # 9. 获取元素树
    print("\n=== 元素树 ===")
    source = wda.get_source()
    if source:
        lines = source.split('\n')
        print(f"   元素树行数: {len(lines)}")
        print(f"   前 5 行:")
        for line in lines[:5]:
            print(f"      {line}")
    else:
        print("   ❌ 获取元素树失败")
    
    # 10. 列出已安装应用
    print("\n=== 已安装应用 ===")
    try:
        apps = wda.list_apps()
        print(f"   应用数量: {len(apps)}")
        for app in apps[:5]:
            print(f"   - {app.get('name', 'Unknown')} ({app.get('bundleId', 'N/A')})")
        if len(apps) > 5:
            print(f"   ... 还有 {len(apps) - 5} 个应用")
    except Exception as e:
        print(f"   ❌ 获取应用列表失败: {e}")
    
    # 11. 按 Home 键
    print("\n=== 按 Home 键 ===")
    wda.press_home()
    print("   ✅ Home 键已按下")
    
    # 12. 启动设置应用
    print("\n=== 启动设置应用 ===")
    try:
        wda.launch_app("com.apple.Preferences")
        print("   ✅ 设置应用已启动")
    except Exception as e:
        print(f"   ❌ 启动失败: {e}")
    
    # 等待应用加载
    import time
    time.sleep(2)
    
    # 13. 查找元素
    print("\n=== 查找元素 ===")
    try:
        element_id = wda.find_element("name", "无线局域网")
        if element_id:
            print(f"   ✅ 找到元素: {element_id}")
            
            # 获取元素属性
            text = wda.get_element_text(element_id)
            print(f"   元素文本: {text}")
            
            rect = wda.get_element_rect(element_id)
            print(f"   元素位置: {rect}")
        else:
            print("   ⚠️  未找到元素")
    except Exception as e:
        print(f"   ❌ 查找失败: {e}")
    
    # 14. 滑动操作
    print("\n=== 滑动操作 ===")
    try:
        wda.swipe(from_x=200, from_y=500, to_x=200, to_y=200, duration=0.5)
        print("   ✅ 向上滑动完成")
    except Exception as e:
        print(f"   ❌ 滑动失败: {e}")
    
    # 15. 点击坐标
    print("\n=== 点击坐标 ===")
    try:
        wda.tap(x=200, y=300)
        print("   ✅ 坐标点击完成")
    except Exception as e:
        print(f"   ❌ 点击失败: {e}")
    
    # 16. 获取弹窗
    print("\n=== 检查弹窗 ===")
    try:
        alert_text = wda.get_alert_text()
        if alert_text:
            print(f"   弹窗文本: {alert_text}")
        else:
            print("   无弹窗")
    except Exception as e:
        print(f"   无弹窗")
    
    # 17. 剪贴板操作
    print("\n=== 剪贴板操作 ===")
    try:
        wda.set_clipboard("Hello from DAgent!")
        clipboard = wda.get_clipboard()
        print(f"   剪贴板内容: {clipboard}")
    except Exception as e:
        print(f"   ❌ 剪贴板操作失败: {e}")
    
    # 18. 删除会话
    print("\n=== 删除会话 ===")
    wda.delete_session()
    print("   ✅ 会话已删除")
    
    print("\n✅ 示例完成!")

if __name__ == "__main__":
    main()
