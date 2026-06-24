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
from agent.perception.ui_parser import parse_wda_xml
from agent.helpers import _to_float

class IOSWDADevice(Device):
    """iOS WebDriverAgent 的 Device 实现。"""

    def __init__(self, wda_client: Any, artifact_dir: str | Path = ".artifacts"):
        self.client = wda_client
        self.set_artifact_dir(artifact_dir)

    def set_artifact_dir(self, artifact_dir: str | Path) -> None:
        """绑定当前任务的资源目录。

        设计方案 6.3 要求每个 Task 独立资源隔离：
        task_{id}/screenshots/ 只保存该任务截图。
        """
        self.artifact_dir = Path(artifact_dir)
        self.screenshot_dir = self.artifact_dir / "screenshots"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def check_status(self) -> DeviceStatus:
        started = time.time()
        try:
            self.client.get_status()
            locked = self._safe_call("is_locked", default=False)
            active_app = self._safe_call("get_active_app_info", default={}) or {}
            battery = self._safe_call("get_battery_info", default={}) or {}
            orientation = self._safe_call("get_orientation", default="portrait") or "portrait"
            return DeviceStatus(
                connection=ConnectionState.CONNECTED,
                is_locked=bool(locked),
                foreground_app=str(active_app.get("bundleId") or active_app.get("name") or ""),
                screen_on=True,
                network_reachable=True,
                battery_level=float(battery.get("level", -1) if isinstance(battery, dict) else -1),
                orientation=str(orientation).lower(),
                healthy=not bool(locked),
                message=f"WDA connected ({time.time() - started:.2f}s)",
            )
        except Exception as exc:
            return DeviceStatus(connection=ConnectionState.DISCONNECTED, healthy=False, message=str(exc))

    def capture_screen(self) -> ScreenCapture:
        ts = time.time()
        screenshot_path = ""
        raw_source = ""
        try:
            b64 = self.client.get_screenshot()
            if b64:
                screenshot_path = str(self.screenshot_dir / f"screen_{int(ts * 1000)}.jpg")
                Path(screenshot_path).write_bytes(base64.b64decode(b64))
        except Exception:
            pass
        try:
            raw_source = self.client.get_source()
        except Exception as exc:
            raw_source = f"<error>{exc}</error>"
        elements = parse_wda_xml(raw_source)
        return ScreenCapture(
            screenshot_path=screenshot_path,
            ui_tree=elements,
            raw_ui_tree=raw_source,
            timestamp=ts,
            metadata={"source_len": len(raw_source)},
        )

    def get_info(self) -> DeviceInfo:
        info = self._safe_call("get_device_info", default={}) or {}
        screen = self._safe_call("get_window_size", default=None) or self._safe_call("get_screen_info", default={}) or {}
        width = int(screen.get("width") or screen.get("screenWidth") or 0) if isinstance(screen, dict) else 0
        height = int(screen.get("height") or screen.get("screenHeight") or 0) if isinstance(screen, dict) else 0
        return DeviceInfo(
            device_id=str(info.get("udid") or info.get("identifier") or "ios-wda"),
            platform=PlatformType.IOS,
            model=str(info.get("model") or info.get("name") or "iOS Device"),
            os_version=str(info.get("osVersion") or info.get("systemVersion") or "unknown"),
            screen_resolution=(width, height),
            pixel_ratio=float(info.get("scale", 1.0) or 1.0),
            capabilities={"ui_tree": True, "screenshot": True, "wda": True},
        )

    def click(self, x: float, y: float) -> OperationResult:
        return self._op("tap", lambda: self.client.tap(int(x), int(y)), {"x": x, "y": y})

    def swipe(self, start_x: float, start_y: float, end_x: float, end_y: float, duration: float = 0.2) -> OperationResult:
        def call():
            # WDA 的 swipe 是方向式；优先使用 drag 保留坐标语义。
            if hasattr(self.client, "drag"):
                return self.client.drag(int(start_x), int(start_y), int(end_x), int(end_y), duration)
            dx, dy = end_x - start_x, end_y - start_y
            direction = "left" if abs(dx) > abs(dy) and dx < 0 else "right" if abs(dx) > abs(dy) else "up" if dy < 0 else "down"
            return self.client.swipe(direction=direction, velocity=1000, x=int(start_x), y=int(start_y))

        return self._op("swipe", call, {"start_x": start_x, "start_y": start_y, "end_x": end_x, "end_y": end_y})

    def input_text(self, text: str) -> OperationResult:
        def call():
            active = self._safe_call("get_active_element", default=None)
            if active and hasattr(self.client, "send_keys"):
                return self.client.send_keys(active, text)
            if hasattr(self.client, "keyboard_input"):
                return self.client.keyboard_input("0", list(text))
            if hasattr(self.client, "send_global_keys"):
                return self.client.send_global_keys(text)
            raise RuntimeError("WDA client does not support text input")

        return self._op("input_text", call, {"text": text})

    def press_back(self) -> OperationResult:
        def call():
            for name in ("返回", "Back", "back", "取消", "关闭"):
                eid = self._safe_call("find_element", "name", name, default=None)
                if eid:
                    return self.client.click_element(eid)
            info = self.get_info()
            w, h = info.screen_resolution
            if w and h:
                return self.swipe(5, h / 2, w * 0.45, h / 2).raw_response
            raise RuntimeError("未找到返回按钮，且无法获取屏幕尺寸执行返回手势")

        return self._op("press_back", call, {})

    def press_home(self) -> OperationResult:
        return self._op("press_home", self.client.press_home, {})

    def wait(self, seconds: float) -> OperationResult:
        seconds = max(0.1, min(float(seconds), 30.0))
        return self._op("wait", lambda: time.sleep(seconds), {"seconds": seconds})

    def _safe_call(self, method: str, *args: Any, default: Any = None, **kwargs: Any) -> Any:
        try:
            fn = getattr(self.client, method)
            return fn(*args, **kwargs)
        except Exception:
            return default

    def _op(self, name: str, fn: Any, params: Dict[str, Any]) -> OperationResult:
        started = time.time()
        try:
            raw = fn()
            return OperationResult(True, f"{name} success", raw_response=raw, duration=time.time() - started)
        except Exception as exc:
            return OperationResult(False, f"{name} failed: {exc}", duration=time.time() - started, raw_response={"params": params})


