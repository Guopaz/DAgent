"""
感知层（PerceptionLayer）。

核心职责：封装设备交互，输出结构化的 Observation。
- observe(): 调用设备获取截图和 UI 树，组装为 Observation 对象
- _infer_page_name(): 从 UI 元素推断当前页面名称（优先导航栏，回退到首个文本元素）
- _available_actions(): 根据当前页面元素类型推断可用动作（有按钮则可点击，有输入框则可输入等）
- 内部使用 ChangeDetector 检测页面变化（新增/移除/修改的元素）
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
from device_factory import ensure_device
from agent.perception.change_detector import ChangeDetector

# PerceptionLayer: 感知层，封装设备交互，输出结构化的 Observation
# 内部使用 ChangeDetector 检测页面变化
class PerceptionLayer:
    def __init__(self, device: Any):
        self.device = ensure_device(device)
        self.detector = ChangeDetector()

    def observe(self) -> Observation:
        status = self.device.check_status()
        info = self.device.get_info()
        capture = self.device.capture_screen()
        obs = Observation(
            page_name=self._infer_page_name(capture.ui_tree),
            elements=capture.ui_tree,
            screenshot_path=capture.screenshot_path,
            raw_ui_tree=capture.raw_ui_tree,
            device_status=status,
            device_info=info,
            page_metadata=capture.metadata,
            available_actions=self._available_actions(capture.ui_tree),
        )
        obs.diff_from_previous = self.detector.detect_changes(obs)
        return obs

    @staticmethod
    def _infer_page_name(elements: List[UIElement]) -> str:
        for el in elements:
            if el.type == ElementType.NAVIGATION_BAR and el.semantic_text:
                return el.semantic_text
        for el in elements:
            if el.type in {ElementType.STATIC_TEXT, ElementType.BUTTON} and el.semantic_text:
                return el.semantic_text[:40]
        return "unknown"

    @staticmethod
    def _available_actions(elements: List[UIElement]) -> List[str]:
        actions: list[str] = []
        if any(e.clickable for e in elements):
            actions.append("click")
        if any(e.type in {ElementType.TEXT_FIELD, ElementType.SEARCH_FIELD, ElementType.SECURE_TEXT_FIELD} for e in elements):
            actions.append("input")
        if any(e.type in {ElementType.TABLE, ElementType.CELL} for e in elements):
            actions.extend(["swipe_up", "swipe_down"])
        actions.extend(["back", "home", "wait"])
        return sorted(set(actions))


