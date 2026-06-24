"""
工作流数据结构（Workflow）。

将 Task 转换为可执行的工作流：
- 持有 TaskGoal（含 success_criteria）和 TaskProgress
- build_decision_context(): 构建 Planner 决策所需的 ExecutionContext
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
from agent.memory import Memory

# Workflow: 工作流数据结构，持有 TaskGoal 和 TaskProgress
# build_decision_context() 构建 Planner 决策所需的 ExecutionContext
@dataclass
class Workflow:
    task_id: str
    goal: TaskGoal
    progress: TaskProgress
    current_node: str = "observe"
    status: str = "running"

    def build_decision_context(
        self,
        observation: Observation,
        device_status: DeviceStatus,
        device_info: DeviceInfo,
        memory: Memory,
        state: AgentRunState,
    ) -> ExecutionContext:
        return ExecutionContext(self.goal, self.progress, observation, device_status, device_info, memory, state)


