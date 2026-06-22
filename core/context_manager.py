"""消息上下文管理器 — 控制对话中屏幕状态的注入和淘汰"""

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .screen_monitor import ScreenMonitor

SCREEN_MARKER = "<screen-state>"
SCREEN_MARKER_END = "</screen-state>"


class MessageContextManager:
    """
    消息上下文管理器

    职责：
    - 在每轮 LLM 调用前注入最新屏幕状态
    - 淘汰消息历史中的旧屏幕帧
    - 控制屏幕内容在上下文中的 token 预算
    - 管理自动观察消息的格式

    设计原则：
    - 屏幕状态作为 system 消息注入，不参与 tool_call 配对
    - 只保留最新一帧，旧帧替换为摘要引用
    - 屏幕内容 token 预算可配置
    """

    def __init__(
        self,
        screen_token_budget: int = 8000,
        use_summary: bool = True,
        inject_mode: str = "summary",
    ):
        """
        Args:
            screen_token_budget: 屏幕内容最大 token 预算
            use_summary: 是否使用精简摘要（True）或完整 XML（False）
            inject_mode: 注入模式
                - "summary": 只注入摘要（最省 token）
                - "xml": 注入完整 XML
                - "both": 摘要 + 截断 XML
        """
        self.screen_token_budget = screen_token_budget
        self.use_summary = use_summary
        self.inject_mode = inject_mode

    def inject_screen_state(
        self,
        messages: list,
        monitor: 'ScreenMonitor',
    ) -> None:
        """
        在 messages 中注入最新屏幕状态

        注入策略（解决 LLM API 消息序列兼容性问题）：
        - 动态修改第一条 system 消息的末尾，追加屏幕状态
        - 避免在 assistant/tool 消息之间插入 system 消息（会破坏 API 规范）
        - 旧屏幕状态自动替换，只保留最新一帧

        注入内容示例：
        ```
        <screen-state>
        📱 当前屏幕：
        导航栏: 设置 > 无线局域网
        可见元素:
          🔘 [Button] "返回"
          🔀 [Switch] "无线局域网"
          📑 Tab: "Wi-Fi", "蓝牙", "蜂窝"

        变化: 新增元素: "MyNetwork"；消失元素: "搜索中..."
        </screen-state>
        ```
        """
        # 先淘汰旧屏幕
        self.retire_old_screens(messages)

        # 构建注入内容
        state = monitor.get_screen_state()
        changes = monitor.detect_changes()

        if self.inject_mode == "summary":
            content = f"\n\n{SCREEN_MARKER}\n{state['summary']}\n"
            if changes:
                content += f"\n变化: {changes}\n"
            content += SCREEN_MARKER_END
        elif self.inject_mode == "xml":
            content = f"\n\n{SCREEN_MARKER}\n{state['xml']}\n{SCREEN_MARKER_END}"
        else:  # both
            content = f"\n\n{SCREEN_MARKER}\n{state['summary']}\n"
            if changes:
                content += f"\n变化: {changes}\n"
            content += f"\n<xml>\n{state['xml']}\n</xml>\n"
            content += SCREEN_MARKER_END

        # 找到第一条 system 消息，在其末尾追加屏幕状态
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = msg.get("content", "") + content
                break
        else:
            # 如果没有 system 消息，在开头插入一条
            messages.insert(0, {
                "role": "system",
                "content": content.lstrip(),
            })

    def retire_old_screens(self, messages: list) -> None:
        """
        淘汰消息列表中的旧屏幕帧

        策略：
        - 扫描所有 messages，找到包含 SCREEN_MARKER 的 system 消息
        - 将 system 消息中的旧 <screen-state>...</screen-state> 块替换为简短引用
        - 只保留最新一帧的完整内容

        这确保 messages 中永远只有一帧完整屏幕状态。
        """
        for msg in messages:
            if msg.get("role") != "system":
                continue
            content = msg.get("content", "")
            if SCREEN_MARKER not in content:
                continue

            # 找到所有 <screen-state>...</screen-state> 块
            pattern = rf'{re.escape(SCREEN_MARKER)}.*?{re.escape(SCREEN_MARKER_END)}'
            matches = list(re.finditer(pattern, content, re.DOTALL))

            if len(matches) <= 1:
                continue

            # 保留最后一个，替换之前的
            for match in matches[:-1]:
                content = content[:match.start()] + "（旧屏幕状态已淘汰）" + content[match.end():]

            msg["content"] = content

    def prune_tool_results(self, messages: list, keep_recent: int = 3) -> None:
        """
        裁剪旧的工具执行结果

        对于 role=tool 的消息，只保留最近 keep_recent 条的完整内容，
        更早的替换为摘要引用。

        目的：防止工具结果（特别是 observe_screen 的 XML）无限膨胀。

        Args:
            messages: 消息列表（原地修改）
            keep_recent: 保留最近 N 条完整工具结果
        """
        tool_indices = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "tool":
                tool_indices.append(i)

        # 对超出 keep_recent 的旧工具结果进行裁剪
        to_prune = tool_indices[:-keep_recent] if len(tool_indices) > keep_recent else []

        for idx in to_prune:
            original = messages[idx]["content"]
            if len(original) > 200:
                messages[idx]["content"] = f"[工具结果已裁剪] {original[:100]}..."
