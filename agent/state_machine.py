"""
Agent 状态机（StateMachine）。

核心职责：管理 Agent 运行时的状态转换合法性。
- 定义允许的状态转换路径：INIT → OBSERVING → PLANNING → EXECUTING → VALIDATING → PROGRESS_UPDATED → OBSERVING（循环）
- transition(): 执行状态转换，非法转换时抛出 RuntimeError
- reset(): 重置到 INIT 状态，用于新任务启动时清理上一任务的状态
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

# StateMachine: 状态机，管理 Agent 运行时状态转换的合法性
# 非法转换时抛出 RuntimeError，支持 reset() 重置到新任务
class StateMachine:
    _allowed = {
        AgentRunState.INIT: {AgentRunState.OBSERVING, AgentRunState.FAILED},
        AgentRunState.OBSERVING: {AgentRunState.PLANNING, AgentRunState.RECOVERING, AgentRunState.FAILED},
        AgentRunState.PLANNING: {AgentRunState.EXECUTING, AgentRunState.VALIDATING, AgentRunState.RECOVERING, AgentRunState.TASK_COMPLETED, AgentRunState.FAILED},
        AgentRunState.EXECUTING: {AgentRunState.VALIDATING, AgentRunState.RECOVERING, AgentRunState.FAILED},
        AgentRunState.VALIDATING: {AgentRunState.PROGRESS_UPDATED, AgentRunState.RECOVERING, AgentRunState.TASK_COMPLETED, AgentRunState.FAILED},
        AgentRunState.PROGRESS_UPDATED: {AgentRunState.OBSERVING, AgentRunState.TASK_COMPLETED},
        AgentRunState.RECOVERING: {AgentRunState.OBSERVING, AgentRunState.FAILED},
    }

    def __init__(self):
        self.state = AgentRunState.INIT

    def reset(self) -> None:
        """重置状态机到初始状态，用于开始新任务"""
        self.state = AgentRunState.INIT

    def transition(self, new_state: AgentRunState) -> None:
        allowed = self._allowed.get(self.state, set())
        if new_state not in allowed and self.state != new_state:
            raise RuntimeError(f"非法状态转换：{self.state.value} -> {new_state.value}")
        self.state = new_state


