"""UI 树解析器 — 将 WDA XML 解析为结构化的 UIElement 列表。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from agent.models import ElementType, Rect, UIElement


class UIParser:
    """解析 WDA 返回的 UI 树 XML，生成 UIElement 列表。"""

    def parse(self, xml_source: str) -> List[UIElement]:
        """解析 XML 源码，返回 UIElement 列表。"""
        if not xml_source:
            return []

        elements: List[UIElement] = []
        try:
            root = ET.fromstring(xml_source)
            self._traverse(root, elements)
        except ET.ParseError:
            pass
        return elements

    def _traverse(self, node: ET.Element, elements: List[UIElement]) -> None:
        """递归遍历 XML 树，提取元素信息。"""
        attrs = node.attrib
        xcui_type = attrs.get("type", "")
        element_type = ElementType.from_xcui(xcui_type)

        frame = self._parse_frame(attrs)
        visible = attrs.get("visible", "1") == "1"
        enabled = attrs.get("enabled", "1") == "1"
        label = attrs.get("label", "")
        name = attrs.get("name", "")
        value = attrs.get("value", "")
        identifier = attrs.get("identifier", "")

        clickable = element_type in (
            ElementType.BUTTON,
            ElementType.CELL,
            ElementType.SWITCH,
            ElementType.TAB_BAR,
            ElementType.NAVIGATION_BAR,
        ) or xcui_type in ("XCUIElementTypeButton", "XCUIElementTypeCell")

        element = UIElement(
            id=identifier or name or f"elem_{len(elements)}",
            type=element_type,
            text=name,
            label=label,
            value=value,
            visible=visible,
            enabled=enabled,
            clickable=clickable,
            frame=frame,
            attributes={
                "xcui_type": xcui_type,
                "identifier": identifier,
            },
        )

        if visible:
            elements.append(element)

        for child in node:
            self._traverse(child, elements)

    def _parse_frame(self, attrs: dict) -> Rect:
        """从属性中解析 frame。"""
        try:
            x = float(attrs.get("x", 0))
            y = float(attrs.get("y", 0))
            width = float(attrs.get("width", 0))
            height = float(attrs.get("height", 0))
            return Rect(x=x, y=y, width=width, height=height)
        except (ValueError, TypeError):
            return Rect()
