"""
Agent 记忆模块（Memory）。

核心职责：在任务执行过程中维护短期记忆，为 Planner 决策提供历史上下文。
- page_history: 页面访问历史（仅存页面名称），用于导航类任务验证
- action_history: 动作执行历史（最近 50 条），LLM 决策时取最近 8 条
- failures: 失败记录（验证未通过或执行失败的动作），LLM 决策时取最近 5 条
- recoveries: 恢复策略记录，用于追踪恢复效果
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

# Memory: 短期记忆，维护页面历史、动作历史、失败记录和恢复记录
# 为 Planner 决策提供最近 8 个动作和最近 5 个失败的上下文
class Memory:
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.task_history: list[dict[str, Any]] = []
        self.page_history: list[str] = []
        self.action_history: list[dict[str, Any]] = []
        self.failures: list[dict[str, Any]] = []
        self.recoveries: list[dict[str, Any]] = []

    def remember_page(self, observation: Observation) -> None:
        self.page_history.append(observation.page_name)
        self.page_history = self.page_history[-self.max_history :]

    def remember_action(self, record: ActionRecord, validation: ValidationResult) -> None:
        item = {
            "action": record.action.type.value,
            "target": record.action.target,
            "value": record.action.value,
            "method": record.device_method,
            "success": record.result.success,
            "validation_passed": validation.passed,
            "message": validation.message,
            "timestamp": record.timestamp,
        }
        self.action_history.append(item)
        self.action_history = self.action_history[-self.max_history :]
        if not validation.passed or not record.result.success:
            self.failures.append(item)
            self.failures = self.failures[-self.max_history :]

    def recent_actions(self, n: int = 5) -> list[dict[str, Any]]:
        return self.action_history[-n:]


