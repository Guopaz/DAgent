"""
知识库增强示例 - 展示如何利用知识库提升 Agent 的上下文理解

运行方式:
  cd DAgent/examples
  python example_with_knowledge.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import iOSAgent
from knowledge import AppKnowledge

def main():
    # 1. 加载知识库
    print("📚 加载 iOS 设置应用知识库...")
    knowledge = AppKnowledge("../knowledge")
    
    # 显示知识库内容
    if "com.apple.Preferences" in knowledge.apps:
        app_data = knowledge.apps["com.apple.Preferences"]["data"]
        print(f"\n   应用: {app_data.get('name')}")
        print(f"   描述: {app_data.get('description')}")
        
        # 显示页面信息
        pages = app_data.get("pages", {})
        print(f"\n   📄 已知页面 ({len(pages)}):")
        for page_name, page_info in pages.items():
            elements_count = len(page_info.get("elements", []))
            print(f"      - {page_name}: {elements_count} 个关键元素")
        
        # 显示操作流程
        flows = app_data.get("flows", {})
        print(f"\n   🔄 操作流程 ({len(flows)}):")
        for flow_name, steps in flows.items():
            print(f"      - {flow_name}: {len(steps)} 步")
    
    # 2. 创建带知识库的 Agent
    print("\n🤖 创建增强型 iOSAgent...")
    agent = iOSAgent(
        wda_url="http://localhost:8100",
        max_steps=30
    )
    
    # 3. 连接 WDA
    print("\n📱 连接 WDA...")
    try:
        agent.connect()
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        return
    
    # 4. 执行任务（知识库会自动提供上下文）
    print("\n🎯 执行任务...")
    
    # 任务 1: 关闭 WiFi（知识库中有详细流程）
    task1 = "关闭无线局域网（WiFi）"
    print(f"\n{'='*60}")
    print(f"任务: {task1}")
    print(f"{'='*60}")
    
    result1 = agent.run(task1)
    print(f"\n✅ 结果: {result1}")
    
    # 任务 2: 查看设备信息
    task2 = "查看设备信息"
    print(f"\n{'='*60}")
    print(f"任务: {task2}")
    print(f"{'='*60}")
    
    result2 = agent.run(task2)
    print(f"\n✅ 结果: {result2}")
    
    # 5. 断开连接
    print("\n👋 断开连接...")
    agent.disconnect()

if __name__ == "__main__":
    main()
