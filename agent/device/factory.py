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

from agent.device.base import Device
from agent.device.ios_wda import IOSWDADevice

def ensure_device(device_or_wda: Any) -> Device:
    if isinstance(device_or_wda, Device):
        return device_or_wda
    return IOSWDADevice(device_or_wda)


