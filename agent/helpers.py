"""
Agent 辅助函数集合。

提供各模块共用的纯函数和工具方法：
- 文本匹配：_loose_contains, _goal_tokens, _match_score — 模糊文本匹配和 token 提取
- 语义验证：_progress_genuinely_satisfies — 区分"正在做"和"已完成"的进度验证
- 元素查找：find_best_element, first_element — UI 元素匹配
- 目标推断：infer_success_criteria — 从任务描述自动推断成功标准
- 文本提取：_extract_search_keyword, _extract_after_keywords — 从目标中提取关键词
- 序列化工具：_safe_asdict, _extract_json — 数据类和 JSON 转换
- UI 工具：visible_element_details, element_detail_dict — 元素详情提取
- 设备参数：_default_swipe_params — 默认滑动参数
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

# 安全转换为 float，失败时返回默认值
def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


# 安全转换为 bool，支持字符串 "1"/"true"/"yes"
def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


# 在元素列表中查找与目标最匹配的元素（按分数和面积排序）
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


# 查找第一个匹配指定类型的可见且启用的元素
def first_element(elements: Iterable[UIElement], types: set[ElementType]) -> Optional[UIElement]:
    return next((e for e in elements if e.visible and e.enabled and e.type in types), None)


# 计算 UI 元素文本与目标文本的匹配分数
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


# 从目标描述中提取关键词 token，过滤停用词
def _goal_tokens(goal: str) -> List[str]:
    # 中文按常见动词/标点切分，英文按词切分；过滤过短和泛化词。
    raw = re.split(r"[\s,，。.!！?？、：:;；/\\]+|打开|启动|进入|点击|选择|搜索|查找|输入|投递|前三个|前3个", goal)
    tokens = [x.strip() for x in raw if len(x.strip()) >= 2]
    stop = {"应用", "按钮", "页面", "任务", "完成", "进行", "相关"}
    return [t for t in tokens if t not in stop]


# 提取指定关键词之后的内容（如"打开"之后的 App 名称）
def _extract_after_keywords(text: str, keywords: List[str]) -> str:
    for kw in keywords:
        if kw in text:
            tail = text.split(kw, 1)[1].strip()
            tail = re.split(r"[,，。.!！?？、\s]", tail)[0]
            return tail[:20]
    return ""


# 提取搜索/输入类任务中的关键词
def _extract_search_keyword(goal: str) -> str:
    for pat in [r"搜索\s*([^,，。；;]+)", r"查找\s*([^,，。；;]+)", r"输入\s*([^,，。；;]+)"]:
        m = re.search(pat, goal)
        if m:
            val = m.group(1).strip()
            # 去掉后续动作描述。
            val = re.split(r"并|后|然后|，|,", val)[0].strip()
            return val
    return ""


# 从任务描述自动推断成功标准（提取"进入"、"发送"、"搜索"等关键词后的内容）
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
    # 处理"发送"类任务：提取要发送的消息内容
    send_match = re.search(r"发送\s*([^,，。；;]+)", goal)
    if send_match:
        message = send_match.group(1).strip()
        # 去掉后续动作描述
        message = re.split(r"并|后|然后|，|,", message)[0].strip()
        if message:
            criteria.append(f"已发送消息{message}")
    if not criteria:
        criteria.append(goal)
    return criteria


# 根据设备屏幕分辨率计算默认滑动参数（起止坐标、持续时间）
# direction: 'up' / 'down' / 'left' / 'right'
def _default_swipe_params(info: DeviceInfo, direction: str = 'up') -> Dict[str, float]:
    w, h = info.screen_resolution
    w = w or 390
    h = h or 844
    cx, cy = w * 0.5, h * 0.5
    if direction == 'up':
        return {"start_x": cx, "start_y": h * 0.75, "end_x": cx, "end_y": h * 0.30, "duration": 0.4}
    elif direction == 'down':
        return {"start_x": cx, "start_y": h * 0.30, "end_x": cx, "end_y": h * 0.75, "duration": 0.4}
    elif direction == 'left':
        return {"start_x": w * 0.80, "start_y": cy, "end_x": w * 0.20, "end_y": cy, "duration": 0.4}
    elif direction == 'right':
        return {"start_x": w * 0.20, "start_y": cy, "end_x": w * 0.80, "end_y": cy, "duration": 0.4}
    else:
        raise ValueError(f"不支持的滑动方向: {direction}")


# 判断是否为导航返回类任务（包含"返回上一页"等关键词）
def _is_navigation_back_goal(description: str, criteria: List[str]) -> bool:
    text = " ".join([description] + list(criteria))
    return any(k in text for k in ["返回上一页", "返回上一级", "回到上一页", "回上一页", "返回前一页"])


# 检查文本是否包含目标标准的任意 token（模糊匹配）
def _loose_contains(text: str, criterion: str) -> bool:
    tokens = _goal_tokens(criterion) or [criterion]
    return any(t and t in text for t in tokens)


# 从 LLM 返回的文本中提取 JSON 对象（处理 markdown 代码块和多余文本）
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


# 安全地将 dataclass 对象转换为字典，处理枚举、datetime 等特殊类型
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


# 将单个 UIElement 转换为包含 name、center、bounds 的详情字典
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


# 提取所有可见元素的详情字典，用于传递给 LLM 的 prompt
def visible_element_details(elements: Iterable[UIElement]) -> List[Dict[str, Any]]:
    return [element_detail_dict(e) for e in elements if e.visible]


# 压缩 Observation 对象用于报告存储，限制元素数量避免文件过大
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



# 语义验证进度是否真正满足成功标准，区分"正在做"和"已完成"，避免文本子串匹配导致的幻觉
def _progress_genuinely_satisfies(progress_objectives: list, criteria: list) -> bool:
    """验证进度目标是否真正满足成功标准，而非仅靠文本子串匹配。

    核心原则：进度条目描述的是"正在做"还是"已完成"，必须有语义区分。
    例如"正在查找福宝有限公司"不等于"已进入福宝有限公司的对话"。
    """
    if not progress_objectives or not criteria:
        return False

    # 动作完成标记词：出现在 progress 条目中说明该步骤已完成
    completion_markers = ["已", "完成", "成功", "切换了", "进入了", "打开了", "点击了", "发送了"]
    # 动作进行中标记词：说明该步骤还在执行中，尚未完成
    in_progress_markers = ["正在", "查找", "搜索中", "尝试", "寻找", "滚动"]

    for criterion in criteria:
        criterion_tokens = _goal_tokens(criterion) or [criterion]
        found = False
        for obj in progress_objectives:
            # 检查此 progress 条目是否声称完成了该标准
            obj_has_completion = any(m in obj for m in completion_markers)
            obj_has_in_progress = any(m in obj for m in in_progress_markers)

            # 如果 progress 条目只是"正在查找X"，不能说"已进入X"已满足
            if obj_has_in_progress and not obj_has_completion:
                continue

            # 检查 progress 条目是否包含成功标准的关键 token
            if any(t and t in obj for t in criterion_tokens):
                # 额外检查：progress 条目描述的动作是否与成功标准语义一致
                # 例如 criterion 是"已进入福宝有限公司的对话"，progress 是"切换到消息tab"
                # 虽然可能碰巧包含"福宝有限公司"文本，但"切换到消息tab"和"进入对话"是不同的动作
                criterion_verbs = [v for v in ["进入", "点击", "发送", "输入", "搜索", "打开", "投递", "提交"] if v in criterion]
                progress_verbs = [v for v in ["进入", "点击", "发送", "输入", "搜索", "打开", "投递", "提交", "切换"] if v in obj]
                # 如果 criterion 要求特定动作（如"进入"），progress 必须包含相同或兼容的动作
                if criterion_verbs and not progress_verbs:
                    continue
                found = True
                break

        if not found:
            return False
    return True
