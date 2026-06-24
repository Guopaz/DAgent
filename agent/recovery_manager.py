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
from agent.device.factory import ensure_device

class RecoveryManager:
    def __init__(self, device: Any = None, wda: Any = None, max_retries: int = 3):
        self.device = ensure_device(device or wda) if (device or wda) is not None else None
        self.max_retries = max_retries
        self.recovery_count = 0

    def recover(self, context: ExecutionContext, validation: Optional[ValidationResult] = None) -> RecoveryStrategy:
        self.recovery_count += 1
        if self.recovery_count <= self.max_retries:
            if self.device:
                self.device.wait(1.0)
            return RecoveryStrategy.RETRY
        if self.recovery_count <= self.max_retries + 2:
            if self.device:
                self.device.press_back()
                self.device.wait(1.0)
            return RecoveryStrategy.REPLAN
        return RecoveryStrategy.ABORT_TASK


