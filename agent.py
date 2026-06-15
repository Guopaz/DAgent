"""iPhone WDA 自动化的核心 ReAct Agent 循环。"""
from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from dotenv import load_dotenv
from tools import ToolExecutor, get_tools
from wda_client import WDAClient
from knowledge import AppKnowledge

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


SYSTEM_PROMPT = """你是一个 iPhone 自动化测试 Agent。你通过 WebDriverAgent (WDA) 控制一台真实的 iPhone 设备。

你的目标是通过观察屏幕并逐步执行操作来完成用户指定的任务。

## 工作流程（ReAct 循环）
每一步：
1. **观察**：调用 get_source（必要时调用 get_screenshot）来查看当前屏幕内容。
2. **思考**：分析当前状态，判断下一步应该做什么，选择哪个工具。
3. **行动**：调用合适的工具执行操作。
4. **验证**：操作后再次观察，确认操作成功后再继续。

## 核心原则
- 每次操作前先观察，不要假设屏幕上的内容。
- 优先使用 get_source 作为主要感知工具。仅在需要视觉细节时才使用 get_screenshot。
- 与元素交互前，先用 find_element 定位元素。
- 等待 UI 过渡：点击后，调用 wait(1) 或 wait(2) 再观察。
- 操作失败时，尝试其他策略（换定位方式、滑动查找等）。
- 任务完成后，调用 task_complete 并附上总结。

## 错误恢复
- 找不到元素？尝试：换定位策略、滑动滚动、等待后重试。
- 意外弹窗？先用 get_alert_text 获取内容，然后 accept_alert 或 dismiss_alert。
- 业务弹窗？点击弹窗的关闭按钮，或弹窗上同意和继续之类的按钮。
- 应用无响应？用 launch_app 重新启动。

## 输出格式
每一步用中文简要说明你在做什么以及为什么，然后调用工具。
"""


class iOSAgent:
    def __init__(
        self,
        wda_url: str = "http://localhost:8100",
        llm_model: str | None = None,
        llm_api_key: str | None = None,
        llm_base_url: str | None = None,
        max_steps: int = 30,
    ):
        self.wda = WDAClient(wda_url)
        self.executor = ToolExecutor(self.wda)
        self.llm = OpenAI(
            api_key=llm_api_key or os.getenv("LLM_API_KEY"),
            base_url=llm_base_url or os.getenv("LLM_BASE_URL"),
        )
        self.model = llm_model or os.getenv("LLM_MODEL_ID", "gpt-4o")
        self.max_steps = max_steps
        self.messages: list[dict[str, Any]] = []
        self.knowledge = AppKnowledge(knowledge_dir="knowledge")

    def _build_knowledge_context(self, task: str, page_source: str = "") -> str:
        """根据任务和当前页面，从知识库构建相关上下文"""
        all_context = []
        for bundle_id in self.knowledge.apps:
            ctx = self.knowledge.build_context_for_task(bundle_id, task, page_source)
            if ctx:
                all_context.append(ctx)
        return "\n\n".join(all_context) if all_context else ""

    def connect(self):
        """连接 WDA 并创建会话。"""
        status = self.wda.get_status()
        print(f"✅ WDA 状态: {status.get('value', {}).get('state', 'unknown')}")

        # 创建会话
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

        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

        for step in range(1, self.max_steps + 1):
            print(f"📍 步骤 {step}/{self.max_steps}")

            # 调用 LLM（携带工具定义）
            response = self.llm.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=get_tools(),
                tool_choice="auto",
            )

            msg = response.choices[0].message

            # 将 assistant 消息加入历史
            self.messages.append(msg.model_dump())

            # 打印思考过程
            if msg.content:
                print(f"💭 {msg.content}\n")

            # 没有工具调用 — Agent 认为任务完成
            if not msg.tool_calls:
                return msg.content or "Agent 在未调用 task_complete 的情况下停止了。"

            # 执行每个工具调用
            for tool_call in msg.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                print(f"🔧 {name}({json.dumps(args, ensure_ascii=False)})")

                result = self.executor.execute(name, args)

                # 检查任务完成信号
                if result.startswith("TASK_COMPLETE:"):
                    summary = result.replace("TASK_COMPLETE:", "").strip()
                    print(f"\n✅ 任务完成: {summary}")
                    return summary

                print(f"   → {result[:200]}{'...' if len(result) > 200 else ''}\n")

                # 将工具执行结果加入消息历史
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })

        print(f"\n⚠️  达到最大步数 ({self.max_steps})，停止执行。")
        return "任务未完成：已达到最大步数限制。"

    def close(self):
        self.wda.close()


def main():
    """Agent 交互式命令行入口。"""
    from dotenv import load_dotenv
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
        agent.messages = []

    agent.close()


if __name__ == "__main__":
    main()
