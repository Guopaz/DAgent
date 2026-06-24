"""
设备工厂模块。

提供 ensure_device() 工厂函数：
- 如果传入的已经是 Device 实例，直接返回
- 如果传入的是 WDA client，自动包装为 IOSWDADevice
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

from agent.device.device import Device
from ios.ios_device import IOSWDADevice

def ensure_device(device_or_wda: Any) -> Device:
    if isinstance(device_or_wda, Device):
        return device_or_wda
    return IOSWDADevice(device_or_wda)


