"""iOS 自动化 Agent 交互式入口 — 基于 HelloAgents 框架。"""

import sys
from agent import iOSAgent
from dotenv import load_dotenv

load_dotenv('.env')

def main():
    print("=" * 60)
    print("       iOS 自动化测试 Agent (HelloAgents)")
    print("=" * 60)
    print()

    wda_url = "http://localhost:8100"
    if len(sys.argv) > 1:
        wda_url = sys.argv[1]

    agent = iOSAgent(wda_url)

    try:
        agent.connect()
    except Exception as e:
        print(f"❌ 连接 WDA 失败: {e}")
        print("   请确保：")
        print("   1. WDA 已在 iPhone 上运行")
        print("   2. 设备已通过 USB 连接并信任")
        print("   3. 已执行端口转发: iproxy 8100 8100")
        sys.exit(1)

    print()
    print("输入测试任务（输入 'quit' 退出）：")
    print()

    while True:
        try:
            task = input("🎯 > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if task.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        if not task:
            continue

        try:
            agent.run(task)
        except KeyboardInterrupt:
            print("\n⚠️  任务被用户中断")
            continue
        except Exception as e:
            print(f"❌ 执行出错: {e}")
            continue

    agent.disconnect()


if __name__ == "__main__":
    main()
