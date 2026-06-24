"""
WDA XML 解析器。

核心职责：将 WebDriverAgent 返回的 XML UI 树解析为 UIElement 列表。
- parse_wda_xml(): 解析 XML 字符串，提取每个元素的类型、文本、位置、可交互性等属性
- map_wda_type(): 将 WDA 的 XCUIElementType 映射为内部 ElementType 枚举
"""

from __future__ import annotations

import base64
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from agent.models import *
from agent.helpers import _to_bool, _to_float

def parse_wda_xml(source: str) -> List[UIElement]:
    if not source or source.startswith("<error>"):
        return []
    try:
        root = ET.fromstring(source.encode("utf-8"))
    except Exception:
        return []

    elements: list[UIElement] = []
    for idx, node in enumerate(root.iter()):
        attrs = dict(node.attrib)
        type_raw = attrs.get("type") or node.tag
        frame = Rect(
            x=_to_float(attrs.get("x")),
            y=_to_float(attrs.get("y")),
            width=_to_float(attrs.get("width")),
            height=_to_float(attrs.get("height")),
        )
        etype = map_wda_type(type_raw)
        enabled = _to_bool(attrs.get("enabled"), True)
        visible = _to_bool(attrs.get("visible"), True)
        clickable = enabled and visible and etype in {ElementType.BUTTON, ElementType.CELL, ElementType.SWITCH, ElementType.SEARCH_FIELD, ElementType.TEXT_FIELD}
        name = attrs.get("name", "")
        label = attrs.get("label", "")
        value = attrs.get("value", "")
        text = attrs.get("text") or name or label
        elements.append(
            UIElement(
                id=attrs.get("id") or attrs.get("elementId") or f"xml-{idx}",
                type=etype,
                text=str(text or ""),
                label=str(label or ""),
                value=str(value or ""),
                visible=visible,
                enabled=enabled,
                clickable=clickable,
                frame=frame,
                attributes={k: str(v) for k, v in attrs.items()},
            )
        )
    return elements


def map_wda_type(type_raw: str) -> ElementType:
    t = (type_raw or "").lower()
    if "button" in t:
        return ElementType.BUTTON
    if "securetextfield" in t or "secure_text" in t:
        return ElementType.SECURE_TEXT_FIELD
    if "searchfield" in t:
        return ElementType.SEARCH_FIELD
    if "textfield" in t or "textview" in t:
        return ElementType.TEXT_FIELD
    if "statictext" in t:
        return ElementType.STATIC_TEXT
    if "cell" in t:
        return ElementType.CELL
    if "image" in t:
        return ElementType.IMAGE
    if "switch" in t:
        return ElementType.SWITCH
    if "slider" in t:
        return ElementType.SLIDER
    if "table" in t or "collectionview" in t or "scrollview" in t:
        return ElementType.TABLE
    if "navigationbar" in t:
        return ElementType.NAVIGATION_BAR
    if "tabbar" in t:
        return ElementType.TAB_BAR
    if "alert" in t:
        return ElementType.ALERT
    if "keyboard" in t or "key" in t:
        return ElementType.KEYBOARD
    return ElementType.OTHER


