"""
Agent 执行器（Executor）。

核心职责：将 Planner 输出的抽象 Action 转换为具体的设备操作。
- execute(): 根据 ActionType 调用对应的 Device 方法（click/swipe/input/back/home/wait）
- 对 click 动作：优先使用 element_id 定位元素坐标，回退到语义匹配
- 对 input 动作：先点击输入框聚焦，再调用设备输入文本
- 对 swipe 动作：使用默认屏幕参数计算滑动起止点
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
from agent.helpers import _default_swipe_params, _to_float, find_best_element, first_element

# Executor: 执行器，将抽象 Action 转换为具体的设备操作
# 根据 ActionType 调用对应的 Device 方法
class Executor:
    def __init__(self, device: Any):
        self.device = ensure_device(device)

    def execute(self, action: Action, observation: Observation) -> ActionRecord:
        started = time.time()
        method = "unknown"
        params: dict[str, Any] = {}
        result: OperationResult

        if action.type == ActionType.CLICK:
            el = None
            if action.element_id:
                el = next((e for e in observation.elements if e.id == action.element_id and e.visible and e.enabled), None)
                if not el:
                    result = OperationResult(False, f"未找到指定元素ID：{action.element_id} target={action.target}")
                    method = "click"
                else:
                    x, y = el.frame.center
                    method = "click"
                    params = {
                        "x": x,
                        "y": y,
                        "target": action.target,
                        "element_id": action.element_id,
                        "matched": el.semantic_text,
                    }
                    result = self.device.click(x, y)
            else:
                # 兼容旧规则/旧日志：未绑定 element_id 时才使用历史定位方式。
                # LLM 决策路径必须提供 element_id，避免执行阶段再次做不可控语义匹配。
                el = find_best_element(observation.elements, action.target, clickable_only=True) or find_best_element(observation.elements, action.target)
                if not el:
                    result = OperationResult(False, f"未找到目标元素：{action.target}")
                    method = "click"
                else:
                    x, y = el.frame.center
                    method = "click"
                    params = {"x": x, "y": y, "target": action.target, "matched": el.semantic_text}
                    result = self.device.click(x, y)
        elif action.type == ActionType.INPUT:
            # 如果目标输入框可见，先点击聚焦，再输入。
            el = None
            if action.element_id:
                el = next((e for e in observation.elements if e.id == action.element_id and e.visible and e.enabled), None)
            if not el:
                el = find_best_element(observation.elements, action.target) or first_element(
                    observation.elements, {ElementType.SEARCH_FIELD, ElementType.TEXT_FIELD, ElementType.SECURE_TEXT_FIELD}
                )
            if el:
                x, y = el.frame.center
                self.device.click(x, y)
                time.sleep(0.2)
            method = "input_text"
            params = {"text": action.value, "target": action.target, "element_id": action.element_id}
            result = self.device.input_text(action.value)
        elif action.type == ActionType.SWIPE_UP:
            method = "swipe"
            params = _default_swipe_params(observation.device_info, up=True)
            result = self.device.swipe(**params)
        elif action.type == ActionType.SWIPE_DOWN:
            method = "swipe"
            params = _default_swipe_params(observation.device_info, up=False)
            result = self.device.swipe(**params)
        elif action.type == ActionType.BACK:
            method = "press_back"
            result = self.device.press_back()
        elif action.type == ActionType.HOME:
            method = "press_home"
            result = self.device.press_home()
        elif action.type == ActionType.WAIT:
            method = "wait"
            seconds = _to_float(action.value, 2.0) or 2.0
            params = {"seconds": seconds}
            result = self.device.wait(seconds)
        else:
            result = OperationResult(False, f"暂不支持动作类型：{action.type}")

        return ActionRecord(action=action, device_method=method, parameters=params, result=result, duration=time.time() - started)


