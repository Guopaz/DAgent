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
from agent.memory import Memory

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


