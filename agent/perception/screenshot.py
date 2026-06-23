"""截图采集器 — 从 WDA 获取设备截图。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.wda.client import WDAClient


class Screenshot:
    """截图采集器。"""

    def __init__(self, wda: WDAClient):
        self.wda = wda

    def capture(self) -> str:
        """采集当前屏幕截图，返回 base64 编码字符串。"""
        try:
            return self.wda.get_screenshot()
        except Exception:
            return ""
