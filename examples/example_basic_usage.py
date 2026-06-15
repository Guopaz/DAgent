"""
基础使用示例 - 展示如何使用 iOSAgent 执行自动化任务

运行方式:
  cd DAgent/examples
  python example_basic_usage.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import iOSAgent
from knowledge import AppKnowledge

def main():
    # 1. 初始化知识库（可选，用于增强 Agent 的上下文理解）
    print("📚 加载知识库...")
    knowledge = AppKnowledge("../knowledge")
    print(f"   已加载 {len(knowledge.apps)} 个应用知识库")
    
    # 2. 创建 Agent 实例
    print("\n🤖 创建 iOSAgent...")
    agent = iOSAgent(
        wda_url="http://localhost:8100",  # WDA 服务地址
        max_steps=30  # 最大执行步数
    )
    print("   ✅ Agent 初始化完成")
    
    # 3. 连接到 WDA
    print("\n📱 连接到 WDA...")
    try:
        agent.connect()
    except Exception as e:
        print(f"   ❌ 连接失败: {e}")
        print("   请确保:")
        print("   1. iPhone 已连接并信任电脑")
        print("   2. WDA 已在 iPhone 上运行")
        print("   3. 已执行 'iproxy 8100 8100' 端口转发")
        return
    
    # 4. 执行自动化任务
    print("\n🎯 开始执行任务...")
    
    # 示例任务 1: 获取当前屏幕状态
    result1 = agent.run("查看当前屏幕上的内容")
    print(f"\n任务 1 结果: {result1}")
    
    # 示例任务 2: 打开设置应用
    result2 = agent.run("打开设置应用")
    print(f"\n任务 2 结果: {result2}")
    
    # 示例任务 3: 执行更复杂的操作
    result3 = agent.run("在设置中查找并点击'无线局域网'选项")
    print(f"\n任务 3 结果: {result3}")
    
    # 5. 断开连接
    print("\n👋 断开连接...")
    agent.disconnect()
    print("   ✅ 完成")

if __name__ == "__main__":
    main()
