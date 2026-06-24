"""
设备抽象基类（Device）。

定义所有设备实现必须遵循的接口契约：
- check_status(): 检查设备连接状态
- capture_screen(): 截图并获取 UI 树
- get_info(): 获取设备静态信息
- click/swipe/input_text: 交互操作
- press_back/press_home: 系统按键
- wait(): 等待指定时间
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

# Device: 设备抽象基类，定义所有设备实现必须遵循的接口契约
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


