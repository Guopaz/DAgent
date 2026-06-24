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


