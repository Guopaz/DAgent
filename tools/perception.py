"""感知工具 — 观察屏幕状态和检查元素详情。"""

from __future__ import annotations

from typing import List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


class ObserveScreen(WDABaseTool):
    """获取当前屏幕的 UI 元素树（XML）或截图。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="observe_screen",
            description=(
                "获取当前屏幕的 UI 状态。\n"
                "- 默认返回 XML 元素树（模式和 get_source 相同），包含所有元素的 label、name、type、位置信息\n"
                "- 也支持返回截图（mode='screenshot'），返回 base64 PNG，适用于需要视觉判断的场景（如图片、颜色）\n"
                "- XML 超过 25000 字符时自动截断，在最后一个完整标签处切断\n"
                "使用场景：每个操作步骤的第一步，了解当前页面有哪些元素可以交互\n"
                "示例：observe_screen() → 返回 XML 元素树\n"
                "示例：observe_screen(mode='screenshot') → 返回截图 base64"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="mode",
                type="string",
                description="获取模式：'xml'（默认，返回 UI 元素树）或 'screenshot'（返回截图）",
                required=False,
                default="xml",
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        mode = params.get("mode", "xml")

        if mode == "screenshot":
            data = self.wda.get_screenshot()
            if not data:
                return self._fail("无法获取截图（WDA 可能未连接或会话已过期）")
            if len(data) > 30000:
                return self._ok(f"[截图已获取，base64 长度={len(data)}，已截断以节省上下文]")
            return self._ok(data)

        # 默认 XML 模式
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


def create_perception_tools(wda) -> list[WDABaseTool]:
    return [ObserveScreen(wda), InspectElement(wda)]
