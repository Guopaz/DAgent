"""iPhone WDA 自动化 Agent — 基于 HelloAgents 框架的 ReActAgent。"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ReActAgent
from hello_agents.core.config import Config

from tools import build_tool_registry
from wda_client import WDAClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

IOS_AGENT_SYSTEM_PROMPT = """你是一个 iPhone 自动化测试 Agent。你通过 WebDriverAgent (WDA) 控制一台真实的 iPhone 设备。

你的目标是通过观察屏幕并逐步执行操作来完成用户指定的任务。

## 工作流程（ReAct 循环）
每一步：
1. **观察**：调用 get_source（必要时调用 get_screenshot）来查看当前屏幕内容。
2. **思考**：使用 Thought 工具记录你的推理过程，分析当前状态，判断下一步应该做什么。
3. **行动**：调用合适的工具执行操作。
4. **验证**：操作后再次观察，确认操作成功后再继续。

## 核心原则
- 每次操作前先观察，不要假设屏幕上的内容。
- 优先使用 get_source 作为主要感知工具。仅在需要视觉细节时才使用 get_screenshot。
- 与元素交互前，先用 find_element 定位元素。
- 等待 UI 过渡：点击后，调用 wait(1) 或 wait(2) 再观察。
- 操作失败时，尝试其他策略（换定位方式、滑动查找等）。
- 任务完成后，使用 Finish 工具并附上任务总结。
- 使用 Skill 工具加载目标 App 的知识（页面结构、元素定位、操作流程）。

## 错误恢复
- 找不到元素？尝试：换定位策略、滑动滚动、等待后重试。
- 意外弹窗？先用 get_alert_text 获取内容，然后 accept_alert 或 dismiss_alert。
- 业务弹窗？点击弹窗的关闭按钮，或弹窗上同意和继续之类的按钮。
- 应用无响应？用 launch_app 重新启动。

## 输出格式
每一步用中文简要说明你在做什么以及为什么，然后调用工具。
"""


class iOSAgent(ReActAgent):
    """iOS 自动化测试 Agent，继承 HelloAgents ReActAgent。"""

    def __init__(
        self,
        wda_url: str = "http://localhost:8100",
        llm: HelloAgentsLLM | None = None,
        max_steps: int = 30,
    ):
        self.wda = WDAClient(wda_url)

        # Build LLM if not provided
        if llm is None:
            llm = HelloAgentsLLM(
                model=os.getenv("LLM_MODEL_ID"),
                api_key=os.getenv("LLM_API_KEY"),
                base_url=os.getenv("LLM_BASE_URL"),
            )

        # Build tool registry with all WDA tools
        registry = build_tool_registry(self.wda)

        # Config: enable Skills system, disable unused features
        config = Config(
            trace_enabled=False,
            skills_enabled=True,
            skills_dir="skills",
            skills_auto_register=True,
            session_enabled=False,
            subagent_enabled=False,
            todowrite_enabled=False,
            devlog_enabled=False,
        )

        super().__init__(
            name="iOSAgent",
            llm=llm,
            tool_registry=registry,
            system_prompt=IOS_AGENT_SYSTEM_PROMPT,
            config=config,
            max_steps=max_steps,
        )

    def connect(self):
        """连接 WDA 并创建会话。"""
        status = self.wda.get_status()
        print(f"✅ WDA 状态: {status.get('value', {}).get('state', 'unknown')}")
        self.wda.create_session()
        print(f"✅ 会话已创建: {self.wda.session_id}")

    def disconnect(self):
        """close() 的别名。"""
        self.close()

    def run(self, task: str) -> str:
        """执行任务并返回最终总结。"""
        print(f"\n{'='*60}")
        print(f"🎯 任务: {task}")
        print(f"{'='*60}\n")
        return super().run(task)

    def close(self):
        self.wda.close()


def main():
    """Agent 交互式命令行入口。"""
    load_dotenv()
    wda_url = os.getenv("WDA_URL", "http://localhost:8100")
    agent = iOSAgent(wda_url=wda_url)

    print("🤖 iPhone WDA Agent 已就绪。输入任务或 'quit' 退出。\n")
    while True:
        try:
            task = input("📝 任务> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not task or task.lower() in ("quit", "exit", "q"):
            print("再见！")
            break
        agent.run(task)

    agent.close()


if __name__ == "__main__":
    main()
