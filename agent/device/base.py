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

class Device(ABC):
    @abstractmethod
    def check_status(self) -> DeviceStatus: ...

    @abstractmethod
    def capture_screen(self) -> ScreenCapture: ...

    @abstractmethod
    def get_info(self) -> DeviceInfo: ...

    @abstractmethod
    def click(self, x: float, y: float) -> OperationResult: ...

    @abstractmethod
    def swipe(self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float = 0.2) -> OperationResult: ...

    @abstractmethod
    def input_text(self, text: str) -> OperationResult: ...

    @abstractmethod
    def press_back(self) -> OperationResult: ...

    @abstractmethod
    def press_home(self) -> OperationResult: ...

    @abstractmethod
    def wait(self, seconds: float) -> OperationResult: ...


