"""感知工具 — 观察屏幕状态和检查元素详情。"""

from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool

if TYPE_CHECKING:
    from core.screen_monitor import ScreenMonitor


class ObserveScreen(WDABaseTool):
    """获取当前屏幕状态（优先从缓存读取）。"""

    def __init__(self, wda, monitor: Optional[ScreenMonitor] = None):
        super().__init__(
            wda=wda,
            name="observe_screen",
            description=(
                "获取当前屏幕状态。\n"
                "- 屏幕状态在每个操作后自动刷新，此工具从缓存读取，零延迟\n"
                "- mode='summary'（默认）：返回精简摘要\n"
                "- mode='xml'：返回完整 XML 元素树\n"
                "- mode='screenshot'：返回截图 base64（需要实际 WDA 调用）\n"
                "注意：通常无需主动调用此工具，屏幕状态已自动注入到上下文中"
            ),
        )
        self.monitor = monitor  # 可选注入，None 时降级为直接调用 WDA

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="mode",
                type="string",
                description="获取模式：'summary'（默认）/ 'xml' / 'screenshot'",
                required=False,
                default="summary",
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        mode = params.get("mode", "summary")

        # 截图模式：始终需要实际 WDA 调用
        if mode == "screenshot":
            data = self.wda.get_screenshot()
            if not data:
                return self._fail("无法获取截图（WDA 可能未连接或会话已过期）")
            if len(data) > 30000:
                return self._ok(f"[截图已获取，base64 长度={len(data)}，已截断以节省上下文]")
            return self._ok(data)

        # 有缓存时从缓存读取
        if self.monitor and self.monitor.is_valid():
            state = self.monitor.get_screen_state()
            changes = self.monitor.detect_changes()

            if mode == "xml":
                xml = state["xml"]
                if len(xml) > 20000:
                    return self._ok(
                        xml[:20000] + f"\n... [XML 截断，总长度={len(xml)}，"
                        "建议用 inspect_element 查看特定元素]"
                    )
                return self._ok(xml)

            # 默认 summary 模式
            result = state["summary"]
            if changes:
                result += f"\n\n最近变化: {changes}"
            result += f"\n\n📊 快照 #{state['snapshot_count']}"
            return self._ok(result)

        # 降级：无缓存时直接调用 WDA
        source = self.wda.get_source()
        if not source:
            return self._fail("无法获取屏幕 XML（WDA 可能未连接或会话已过期，尝试重新创建会话）")
        return self._ok(self._smart_truncate_xml(source))


class InspectElement(WDABaseTool):
    """检查指定元素的详细信息。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="inspect_element",
            description=(
                "检查指定元素的详细信息（文本内容、属性、位置、状态）。\n"
                "- 自动查询元素的 text、label、type、identifier、enabled、visible、rect\n"
                "- 属性查询失败时返回 'N/A' 而不是整体报错\n"
                "使用场景：先从 observe_screen 获取元素名，再 inspect_element 确认该元素的完整信息\n"
                "示例：inspect_element(name='无线局域网') → 返回该元素的所有属性"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="元素的 label 或 name，从 observe_screen 返回的 XML 中获取",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params["name"]
        element_id = self._find_by_name(name)
        if not element_id:
            return self._fail(f"未找到元素：'{name}'，请先用 observe_screen 确认元素名称是否正确")

        # 逐个属性查询，单个失败不影响整体
        try:
            text = self.wda.get_element_text(element_id) or ""
        except Exception:
            text = "N/A"

        attrs: dict = {}
        for attr in ("label", "type", "identifier"):
            attrs[attr] = self._safe_get_attr(element_id, attr)
        try:
            attrs["enabled"] = bool(self.wda.is_element_enabled(element_id))
        except Exception:
            attrs["enabled"] = "N/A"
        try:
            attrs["visible"] = bool(self.wda.is_element_displayed(element_id))
        except Exception:
            attrs["visible"] = "N/A"
        try:
            rect = self.wda.get_element_rect(element_id) or {}
        except Exception:
            rect = {}

        data = {
            "name": name,
            "element_id": element_id,
            "text": text,
            "attributes": attrs,
            "rect": rect,
        }
        return self._ok(str(data), data=data)


def create_perception_tools(wda, monitor: Optional[ScreenMonitor] = None) -> list[WDABaseTool]:
    return [ObserveScreen(wda, monitor), InspectElement(wda)]
