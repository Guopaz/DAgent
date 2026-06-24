"""
页面变化检测器（ChangeDetector）。

核心职责：对比两次观察结果，检测页面变化。
- detect_changes(): 通过元素 key（类型+文本+位置）对比，识别新增/移除/修改的元素
- _detect_loading(): 检测页面是否处于加载状态（包含"loading""加载中"等关键词）
- 输出 ObservationDiff，包含 page_changed、has_alert、has_keyboard、is_loading 等标志
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

# ChangeDetector: 页面变化检测器，对比两次观察结果识别元素变化
# 检测新增/移除/修改的元素，以及加载状态、弹窗、键盘
class ChangeDetector:
    def __init__(self):
        self.previous: Optional[Observation] = None

    def detect_changes(self, current: Observation) -> ObservationDiff:
        prev = self.previous
        self.previous = current
        current_keys = {self._key(e): e for e in current.elements}
        prev_keys = {self._key(e): e for e in prev.elements} if prev else {}
        added = [e for k, e in current_keys.items() if k not in prev_keys]
        removed = [e for k, e in prev_keys.items() if k not in current_keys]
        changed = [e for k, e in current_keys.items() if k in prev_keys and e.value != prev_keys[k].value]
        return ObservationDiff(
            added=added[:20],
            removed=removed[:20],
            changed=changed[:20],
            page_changed=bool(prev and (added or removed or changed)),
            is_loading=self._detect_loading(current),
            has_alert=any(e.type == ElementType.ALERT for e in current.elements),
            has_keyboard=any(e.type == ElementType.KEYBOARD for e in current.elements),
        )

    @staticmethod
    def _key(e: UIElement) -> str:
        return f"{e.type.value}:{e.semantic_text}:{int(e.frame.x)}:{int(e.frame.y)}"

    @staticmethod
    def _detect_loading(obs: Observation) -> bool:
        text = " ".join(e.semantic_text.lower() for e in obs.elements)
        return any(k in text for k in ["loading", "加载中", "请稍候", "正在载入", "刷新中"])


