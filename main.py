#!/usr/bin/env python3
"""
Mobile Agent - iOS 自动化测试助手

基于 WDA (WebDriverAgent) 的智能 iOS 自动化 Agent。
使用 LLM 进行任务规划、动作决策和状态验证。

使用方法:
    python main.py <wda_url>
    
示例:
    python main.py http://localhost:8100
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径

# 加载 .env 文件
from dotenv import load_dotenv
load_dotenv()
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from wda_client import WDAClient
from agent import (
    AgentLoop,
    PerceptionLayer,
    Planner,
    Executor,
    Validator,
    RecoveryManager,
    Memory,
    Task,
)


def create_agent(wda_url: str = "http://localhost:8100"):
    """创建并初始化 Agent。

    Args:
        wda_url: WDA 服务器 URL

    Returns:
        tuple: (agent_loop, wda_client)
    """
    print("🚀 正在初始化 Mobile Agent...")
    
    # 1. 初始化 WDA 客户端
    print(f"📱 连接到 WDA: {wda_url}")
    wda = WDAClient(wda_url)
    
    try:
        session_id = wda.create_session()
        print(f"✓ WDA 会话已创建: {session_id[:8]}...")
    except Exception as e:
        print(f"✗ 连接 WDA 失败: {e}")
        print("\n请确保:")
        print("  1. WDA 已在 iOS 设备上运行")
        print("  2. 设备已通过 USB 连接并信任")
        print("  3. 已执行端口转发: iproxy 8100 8100")
        sys.exit(1)

    # 2. 初始化 LLM 客户端
    print("🧠 初始化 LLM 客户端...")
    from llm_client import LLMClient
    llm = LLMClient()
    print(f"✓ LLM 客户端已就绪")

    # 3. 初始化各模块
    print("⚙️  初始化 Agent 模块...")
    perception = PerceptionLayer(wda)
    planner = Planner(llm)
    executor = Executor(wda)
    validator = Validator()
    recovery = RecoveryManager(wda=wda, max_retries=3)
    memory = Memory(max_history=50)
    
    # 4. 创建主循环
    agent_loop = AgentLoop(
        wda=wda,
        perception=perception,
        planner=planner,
        executor=executor,
        validator=validator,
        recovery=recovery,
        memory=memory,
        max_actions_per_step=10,
        max_consecutive_failures=5,
    )
    
    print("✓ Agent 初始化完成\n")
    
    return agent_loop, wda


def run_interactive(agent_loop: AgentLoop):
    """交互式运行模式。

    Args:
        agent_loop: Agent 主循环
    """
    print("\n" + "="*60)
    print("🎯 交互式模式 - 输入任务目标，输入 'quit' 退出")
    print("="*60 + "\n")
    
    while True:
        try:
            goal = input("📝 任务目标: ").strip()
            
            if not goal:
                continue
                
            if goal.lower() in ['quit', 'exit', 'q']:
                print("\n👋 再见!")
                break
            
            # 创建并执行任务
            task = Task(goal=goal)
            start_time = time.time()
            
            success = agent_loop.run_task(task)
            
            duration = time.time() - start_time
            print(f"\n任务{'成功' if success else '失败'}，耗时 {duration:.1f} 秒\n")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断，退出程序")
            break
        except Exception as e:
            print(f"\n✗ 执行出错: {e}\n")
            import traceback
            traceback.print_exc()


def run_demo(agent_loop: AgentLoop):
    """运行演示任务。

    Args:
        agent_loop: Agent 主循环
    """
    print("\n" + "="*60)
    print("🎬 演示模式 - 执行预定义任务")
    print("="*60 + "\n")
    
    demo_tasks = [
        "打开设置应用",
        "点击无线局域网",
    ]
    
    for i, goal in enumerate(demo_tasks, 1):
        print(f"\n{'='*60}")
        print(f"演示任务 {i}/{len(demo_tasks)}: {goal}")
        print(f"{'='*60}\n")
        
        task = Task(goal=goal)
        success = agent_loop.run_task(task)
        
        print(f"\n演示任务 {i} {'成功' if success else '失败'}\n")
        
        if not success and i < len(demo_tasks):
            response = input("继续下一个演示任务? (y/n): ").strip()
            if response.lower() != 'y':
                break
        
        time.sleep(2)  # 任务间间隔


def main():
    """主函数"""
    # 解析命令行参数
    wda_url = "http://localhost:8100"
    mode = "interactive"
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] in ['--url', '-u'] and i + 1 < len(args):
            wda_url = args[i + 1]
            i += 2
        elif args[i] in ['--demo', '-d']:
            mode = "demo"
            i += 1
        elif args[i] in ['--help', '-h']:
            print(__doc__)
            print("\n选项:")
            print("  --url, -u <url>    指定 WDA 服务器 URL (默认: http://localhost:8100)")
            print("  --demo, -d         运行演示模式")
            print("  --help, -h         显示帮助信息")
            sys.exit(0)
        else:
            # 可能是旧的 URL 参数格式
            if args[i].startswith('http'):
                wda_url = args[i]
            i += 1
    
    # 创建 Agent
    try:
        agent_loop, wda = create_agent(wda_url)
    except Exception as e:
        print(f"✗ Agent 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # 运行模式
    try:
        if mode == "demo":
            run_demo(agent_loop)
        else:
            run_interactive(agent_loop)
    finally:
        # 清理资源
        print("\n🧹 清理资源...")
        try:
            wda.delete_session()
            print("✓ WDA 会话已关闭")
        except Exception as e:
            print(f"⚠ 关闭 WDA 会话时出错: {e}")


if __name__ == "__main__":
    main()
