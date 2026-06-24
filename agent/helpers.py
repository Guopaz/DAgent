"""自动从旧 agent.py 拆分生成；按职责维护。"""

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

def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def find_best_element(elements: Iterable[UIElement], target: str, clickable_only: bool = False) -> Optional[UIElement]:
    target = (target or "").strip()
    candidates = [e for e in elements if e.visible and e.enabled and (not clickable_only or e.clickable)]
    if not target:
        return candidates[0] if candidates else None
    scored: list[tuple[float, UIElement]] = []
    for el in candidates:
        score = _match_score(el.semantic_text, target)
        if score > 0:
            scored.append((score, el))
    scored.sort(key=lambda x: (x[0], x[1].frame.width * x[1].frame.height), reverse=True)
    return scored[0][1] if scored else None


def first_element(elements: Iterable[UIElement], types: set[ElementType]) -> Optional[UIElement]:
    return next((e for e in elements if e.visible and e.enabled and e.type in types), None)


def _match_score(text: str, target: str) -> float:
    text_l = (text or "").lower()
    target_l = (target or "").lower()
    if not text_l or not target_l:
        return 0.0
    if text_l == target_l:
        return 1.0
    if target_l in text_l or text_l in target_l:
        return 0.8
    tokens = _goal_tokens(target_l)
    if not tokens:
        return 0.0
    hit = sum(1 for t in tokens if t and t in text_l)
    return hit / len(tokens) * 0.6


def _goal_tokens(goal: str) -> List[str]:
    # 中文按常见动词/标点切分，英文按词切分；过滤过短和泛化词。
    raw = re.split(r"[\s,，。.!！?？、：:;；/\\]+|打开|启动|进入|点击|选择|搜索|查找|输入|投递|前三个|前3个", goal)
    tokens = [x.strip() for x in raw if len(x.strip()) >= 2]
    stop = {"应用", "按钮", "页面", "任务", "完成", "进行", "相关"}
    return [t for t in tokens if t not in stop]


def _extract_after_keywords(text: str, keywords: List[str]) -> str:
    for kw in keywords:
        if kw in text:
            tail = text.split(kw, 1)[1].strip()
            tail = re.split(r"[,，。.!！?？、\s]", tail)[0]
            return tail[:20]
    return ""


def _extract_search_keyword(goal: str) -> str:
    for pat in [r"搜索\s*([^,，。；;]+)", r"查找\s*([^,，。；;]+)", r"输入\s*([^,，。；;]+)"]:
        m = re.search(pat, goal)
        if m:
            val = m.group(1).strip()
            # 去掉后续动作描述。
            val = re.split(r"并|后|然后|，|,", val)[0].strip()
            return val
    return ""


def infer_success_criteria(goal: str) -> List[str]:
    criteria: list[str] = []
    if "打开" in goal or "启动" in goal or "进入" in goal:
        app = _extract_after_keywords(goal, ["打开", "启动", "进入"])
        if app:
            criteria.append(f"已进入{app}")
    keyword = _extract_search_keyword(goal)
    if keyword:
        criteria.append(f"已搜索{keyword}")
    m = re.search(r"投递前([一二三四五六七八九十\d]+)个", goal)
    if m:
        criteria.append(f"已成功投递{m.group(1)}个不同目标")
    if not criteria:
        criteria.append(goal)
    return criteria


def _default_swipe_params(info: DeviceInfo, up: bool = True) -> Dict[str, float]:
    w, h = info.screen_resolution
    w = w or 390
    h = h or 844
    return {
        "start_x": w * 0.5,
        "start_y": h * (0.75 if up else 0.30),
        "end_x": w * 0.5,
        "end_y": h * (0.30 if up else 0.75),
        "duration": 0.4,
    }


def _is_navigation_back_goal(description: str, criteria: List[str]) -> bool:
    text = " ".join([description] + list(criteria))
    return any(k in text for k in ["返回上一页", "返回上一级", "回到上一页", "回上一页", "返回前一页"])


def _loose_contains(text: str, criterion: str) -> bool:
    tokens = _goal_tokens(criterion) or [criterion]
    return any(t and t in text for t in tokens)


def _extract_json(content: str) -> Dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    try:
        return json.loads(content)
    except Exception:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise
        return json.loads(m.group(0))


def _safe_asdict(obj: Any) -> Any:
    def convert(v: Any) -> Any:
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, Path):
            return str(v)
        if hasattr(v, "__dataclass_fields__"):
            return {k: convert(getattr(v, k)) for k in v.__dataclass_fields__}
        if isinstance(v, list):
            return [convert(x) for x in v]
        if isinstance(v, tuple):
            return [convert(x) for x in v]
        if isinstance(v, dict):
            return {str(k): convert(val) for k, val in v.items()}
        return v

    return convert(obj)


def element_detail_dict(element: UIElement) -> Dict[str, Any]:
    if hasattr(element, "detail_dict"):
        return element.detail_dict()
    data = _safe_asdict(element)
    frame = data.get("frame", {}) or {}
    x = float(frame.get("x", 0) or 0)
    y = float(frame.get("y", 0) or 0)
    width = float(frame.get("width", 0) or 0)
    height = float(frame.get("height", 0) or 0)
    attrs = data.get("attributes", {}) or {}
    data.update({
        "name": attrs.get("name", ""),
        "center": {"x": x + width / 2, "y": y + height / 2},
        "bounds": {"x": x, "y": y, "width": width, "height": height},
    })
    return data


def visible_element_details(elements: Iterable[UIElement]) -> List[Dict[str, Any]]:
    return [element_detail_dict(e) for e in elements if e.visible]


def _compact_observation(obs: Observation, include_all_elements: bool = True) -> Dict[str, Any]:
    visible_elements = [e for e in obs.elements if e.visible]
    elements = visible_elements if include_all_elements else visible_elements[:50]
    return {
        "page_name": obs.page_name,
        "screenshot_path": obs.screenshot_path,
        "device_status": _safe_asdict(obs.device_status),
        "device_info": _safe_asdict(obs.device_info),
        "element_count": len(obs.elements),
        "visible_element_count": len(visible_elements),
        "elements": [element_detail_dict(e) for e in elements],
        "diff": _safe_asdict(obs.diff_from_previous),
    }


