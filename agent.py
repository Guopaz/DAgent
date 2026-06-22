"""iPhone WDA 自动化 Agent — 基于 HelloAgents 框架的 ReActAgent。"""
from __future__ import annotations

import os

from dotenv import load_dotenv
from hello_agents import HelloAgentsLLM, ReActAgent
from hello_agents.core.config import Config

from core.screen_monitor import ScreenMonitor
from core.context_manager import MessageContextManager
from tools import build_tool_registry
from tools.tool_categories import is_action_tool
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

## 工作流程（ReAct 循环）
每一步：
1. **思考**：根据当前屏幕状态（自动注入），分析当前情况，判断下一步应该做什么。
2. **行动**：调用合适的工具执行操作。操作后屏幕会自动刷新。
3. **验证**：根据新的屏幕状态确认操作是否成功，再继续下一步。

## 核心原则
- 优先使用 tap_element 点击元素（支持 name/xpath/element_id 三种定位方式），找不到时用 scroll_to_find_and_tap。
- 与元素交互前，先从屏幕摘要中了解元素名，必要时用 inspect_element 查看详情。
- 点击后自动等待 1 秒，大多数操作工具内置等待，无需额外调用 wait_seconds。
- 操作失败时，尝试其他策略（换定位方式、scroll_to_find_and_tap 等）。
- 任务完成后，使用 Finish 工具并附上任务总结。

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
        # 每次任务开始前重置屏幕状态
        self.screen_monitor.reset()
        return super().run(task)

    # ---- Hook 实现 ----

    def _on_loop_start(self, messages: list):
        """循环开始前：获取初始屏幕快照"""
        self.screen_monitor.refresh()

    def _before_llm_call(self, messages: list):
        """LLM 调用前：注入最新屏幕状态到 system 消息"""
        self.context_manager.inject_screen_state(messages, self.screen_monitor)

    def _after_tool_execution(self, messages, tool_name, arguments, result):
        """工具执行后：动作工具自动刷新屏幕"""
        if is_action_tool(tool_name, arguments):
            try:
                self.screen_monitor.refresh()
                print(f"📱 屏幕已刷新 (第{self.screen_monitor._snapshot_count}帧)")
            except Exception as e:
                # 降级：标记屏幕状态为过期，让 Agent 主动调用 observe_screen
                self.screen_monitor.mark_stale()
                print(f"⚠️ 屏幕自动刷新失败: {e}，下一步需主动观察")

    def _after_step(self, messages: list, step: int):
        """每步结束后：裁剪旧工具结果，防止消息膨胀"""
        self.context_manager.prune_tool_results(messages, keep_recent=3)

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
