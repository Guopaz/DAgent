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

    def transition(self, new_state: AgentRunState) -> None:
        allowed = self._allowed.get(self.state, set())
        if new_state not in allowed and self.state != new_state:
            raise RuntimeError(f"非法状态转换：{self.state.value} -> {new_state.value}")
        self.state = new_state


