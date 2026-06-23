"""iPhone WDA 自动化 Agent — 基于 HelloAgents 框架的 WorkflowAgent。"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM
from workflow.workflow_agent import WorkflowAgent
from workflow.workflow_engine import WorkflowEngine, NodeTimeout, build_ios_workflow
from workflow.workflow_contexts import DeviceContext, TaskContext, LLMContext
from workflow.workflow_nodes import (
    InitRoutine,
    CleanupRoutine,
    PlanReasoning,
    RefreshRoutine,
    PreCheckRoutine,
    DecideReasoning,
    ExecuteAction,
    VerifyCheckpoint,
    RecoveryReasoning,
    SummaryRoutine,
    StepToolFilter,
)
from hello_agents.core.config import Config

from core.screen_monitor import ScreenMonitor
from core.context_manager import MessageContextManager
from tools import build_tool_registry
from wda_client import WDAClient

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

IOS_AGENT_SYSTEM_PROMPT = """你是一个 iPhone 自动化测试 Agent。你通过 WebDriverAgent (WDA) 控制一台真实的 iPhone 设备。

你的目标是通过观察屏幕并逐步执行操作来完成用户指定的任务。

## 屏幕感知
- 屏幕状态在每个操作后自动刷新，你始终能看到最新页面（注入在 system 消息末尾的 <screen-state> 块中）。
- 无需每次操作前主动调用 observe_screen。
- 如果需要更详细的元素信息，使用 inspect_element。
- 如果需要完整 XML（如写 XPath），使用 observe_screen(mode='xml')。
- 如果需要截图判断视觉内容，使用 observe_screen(mode='screenshot')。

## 工作流程（混合工作流）
整体流程：初始化 → 前置清理 → 任务规划 → 子步骤循环（屏幕刷新 → 前置检查 → 步骤决策 → 执行操作 → 结果验证）→ 任务总结

每个子步骤：
1. **屏幕刷新**：自动获取最新屏幕状态
2. **前置检查**：自动检测并处理弹窗、键盘等阻塞状态
3. **步骤决策**：根据当前屏幕状态和计划，决定本步操作
4. **执行操作**：调用工具执行决策的操作
5. **结果验证**：验证操作是否成功，失败时进入恢复流程

## 核心原则
- 优先使用 tap_element 点击元素（支持 name/xpath/element_id 三种定位方式），找不到时用 scroll_to_find_and_tap。
- 与元素交互前，先从屏幕摘要中了解元素名，必要时用 inspect_element 查看详情。
- 点击后自动等待 1 秒，大多数操作工具内置等待，无需额外调用 wait_seconds。
- 操作失败时，尝试其他策略（换定位方式、scroll_to_find_and_tap 等）。
- 任务完成后，自动进入总结阶段。

## 多 Tab 页面导航（重要）
- 进入多 Tab App（微信、淘宝、Boss直聘等）后，先调用 get_tab_bar(action='list') 了解 Tab 结构。
- get_tab_bar 直接返回当前在哪个 Tab、所有 Tab 列表及索引，零解析成本。
- 切换 Tab: get_tab_bar(action='switch', index=N) 或 get_tab_bar(action='switch', tab_name='名称')
- 纯图标 Tab 无法按名称定位时，用索引切换: get_tab_bar(action='switch', index=3)

## 工具优先级
- tap_element: 首选，支持 name/xpath/element_id 三种定位方式
- go_back: 返回上一页
- input_text: 在输入框中输入文本（name 可选，不提供时自动查找输入框）
- tap_keyboard_return: 输入文本后点击键盘确认键（发送/搜索/完成/提交等）
- scroll_to_find_and_tap: 目标在屏幕外时使用
- get_tab_bar: 多 Tab App 导航，先 list 再 switch
- handle_alert / clear_interrupt: 遇到弹窗/键盘阻塞时使用
- wda_call: 通用 WDA 调用工具，用于高层工具无法覆盖的场景（如坐标点击、双击、拖拽、捏合、旋转、设置方向、按键等）

## 错误恢复
- 找不到元素？尝试 scroll_to_find_and_tap 滚动查找。
- 意外弹窗？先 handle_alert 处理弹窗再继续。
- 业务弹窗？用 handle_alert(action='custom', button_name='同意') 点击弹窗按钮。
- 应用无响应？用 restart_app 重新启动。
- 不确定当前页面？先 clear_interrupt 清理状态，再查看屏幕摘要。

## 输出格式
每一步用中文简要说明你在做什么以及为什么，然后调用工具。
"""


class iOSAgent(WorkflowAgent):
    """iOS 自动化测试 Agent，继承 HelloAgents WorkflowAgent。

    基于混合工作流架构：固定流程 + LLM 决策。
    """

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

        # 创建屏幕监听器和上下文管理器
        self.screen_monitor = ScreenMonitor(self.wda)
        self.context_manager = MessageContextManager(
            screen_token_budget=8000,
            use_summary=True,
            inject_mode="summary",
        )

        # Build tool registry with all WDA tools
        registry = build_tool_registry(self.wda, self.screen_monitor)

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

        # 构建工作流引擎
        workflow = self._build_workflow(registry)

        super().__init__(
            name="iOSAgent",
            llm=llm,
            workflow=workflow,
            tool_registry=registry,
            system_prompt=IOS_AGENT_SYSTEM_PROMPT,
            config=config,
            max_steps=max_steps,
        )

    def _build_workflow(self, registry) -> WorkflowEngine:
        """构建 iOS 自动化工作流"""
        # 创建工具过滤器
        tool_filter = StepToolFilter(registry)

        # 创建引擎
        engine = build_ios_workflow(
            node_timeout=NodeTimeout(),
            global_max_steps=self.max_steps if hasattr(self, "max_steps") else 100,
        )

        # 注册节点
        engine.register_node("init", InitRoutine())
        engine.register_node("cleanup", CleanupRoutine())
        engine.register_node("plan", PlanReasoning())
        engine.register_node("refresh", RefreshRoutine())
        engine.register_node("pre_check", PreCheckRoutine())
        engine.register_node("decide", DecideReasoning(tool_filter=tool_filter))
        engine.register_node("execute", ExecuteAction())
        engine.register_node("verify", VerifyCheckpoint())
        engine.register_node("recovery", RecoveryReasoning())
        engine.register_node("summary", SummaryRoutine())

        return engine

    def connect(self):
        """连接 WDA 并创建会话。"""
        status = self.wda.get_status()
        print(f"✅ WDA 状态: {status.get('value', {}).get('state', 'unknown')}")
        self.wda.create_session()
        print(f"✅ 会话已创建: {self.wda.session_id}")

    def disconnect(self):
        """close() 的别名。"""
        self.close()

    def _build_contexts(self, task: str):
        """构建三个独立上下文（供 run 和 arun 共用）"""
        device_ctx = DeviceContext(wda=self.wda, screen_monitor=self.screen_monitor)
        task_ctx = TaskContext(
            task=task,
            tool_registry=self.tool_registry,
            tool_filter=StepToolFilter(self.tool_registry),
        )
        llm_ctx = LLMContext(
            llm=self.llm,
            messages=[],
            context_manager=self.context_manager,
        )
        return device_ctx, task_ctx, llm_ctx

    def run(self, task: str) -> str:
        """执行任务并返回最终总结。"""
        print(f"\n{'='*60}")
        print(f"🎯 任务: {task}")
        print(f"{'='*60}\n")

        device_ctx, task_ctx, llm_ctx = self._build_contexts(task)
        return self._run_workflow(device_ctx, task_ctx, llm_ctx)

    async def arun(self, task: str, **kwargs) -> str:
        """异步执行任务并返回最终总结。"""
        print(f"\n{'='*60}")
        print(f"🎯 任务: {task}")
        print(f"{'='*60}\n")

        device_ctx, task_ctx, llm_ctx = self._build_contexts(task)
        return await self._arun_workflow(device_ctx, task_ctx, llm_ctx)

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
