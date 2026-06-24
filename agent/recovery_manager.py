"""
Agent 恢复管理器（RecoveryManager）。

核心职责：当动作执行失败或验证不通过时，决定恢复策略。
- recover(): 根据失败次数递增恢复强度：
  1. 前 3 次：等待 1 秒后重试（RETRY）
  2. 第 4-5 次：按返回键后重新规划（REPLAN）
  3. 超过 5 次：放弃任务（ABORT_TASK）
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

# RecoveryManager: 恢复管理器，根据失败次数递增恢复强度
# RETRY(前3次) → REPLAN(4-5次) → ABORT_TASK(超过5次)
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


