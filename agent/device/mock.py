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
from agent.device.base import Device

class MockDevice(Device):
    """离线单测用 Mock 设备。"""

    def __init__(self, elements: Optional[List[UIElement]] = None):
        self.elements = elements or []
        self.info = DeviceInfo(platform=PlatformType.SIMULATOR, screen_resolution=(390, 844), capabilities={"mock": True})

    def check_status(self) -> DeviceStatus:
        return DeviceStatus(connection=ConnectionState.CONNECTED, healthy=True, message="mock")

    def capture_screen(self) -> ScreenCapture:
        return ScreenCapture(ui_tree=self.elements, raw_ui_tree="<mock/>")

    def get_info(self) -> DeviceInfo:
        return self.info

    def click(self, x: float, y: float) -> OperationResult:
        return OperationResult(True, f"mock click {x},{y}")

    def swipe(self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float = 0.2) -> OperationResult:
        return OperationResult(True, "mock swipe")

    def input_text(self, text: str) -> OperationResult:
        return OperationResult(True, f"mock input {text}")

    def press_back(self) -> OperationResult:
        return OperationResult(True, "mock back")

    def press_home(self) -> OperationResult:
        return OperationResult(True, "mock home")

    def wait(self, seconds: float) -> OperationResult:
        return OperationResult(True, f"mock wait {seconds}")


