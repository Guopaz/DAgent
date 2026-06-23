"""WDA 客户端封装 — 复用现有 wda_client.WDAClient，提供 Agent 层所需的接口。"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from wda_client import WDAClient as _WDAClient


class WDAClient:
    """Agent 层使用的 WDA 客户端，包装底层 wda_client.WDAClient。"""

    def __init__(self, base_url: str = "http://localhost:8100"):
        self._client = _WDAClient(base_url)
        self.base_url = base_url
        self.session_id = None

    def create_session(self) -> str:
        self.session_id = self._client.create_session()
        return self.session_id

    def delete_session(self) -> None:
        self._client.delete_session()
        self.session_id = None

    def get_screenshot(self) -> str:
        return self._client.get_screenshot()

    def get_source(self) -> str:
        return self._client.get_source()

    def find_element(self, using: str, value: str):
        return self._client.find_element(using, value)

    def find_elements(self, using: str, value: str):
        return self._client.find_elements(using, value)

    def tap(self, x: float, y: float) -> None:
        self._client.tap(x, y)

    def tap_element(self, element_id: str) -> None:
        self._client.click_element(element_id)

    def type_text(self, element_id: str, text: str) -> None:
        self._client.send_keys(element_id, text)

    def swipe(self, from_x: float, from_y: float, to_x: float, to_y: float, duration: float = 0.5) -> None:
        self._client.swipe(from_x, from_y, to_x, to_y, duration)

    def scroll(self, direction: str = "down") -> None:
        self._client.scroll(direction)

    def get_window_size(self) -> dict:
        return self._client.get_window_rect()

    def launch_app(self, bundle_id: str) -> None:
        self._client.launch_app(bundle_id)

    def terminate_app(self, bundle_id: str) -> None:
        self._client.terminate_app(bundle_id)

    def activate_app(self, bundle_id: str) -> None:
        self._client.activate_app(bundle_id)

    def get_active_app_info(self) -> dict:
        return self._client.get_active_app_info()

    def go_home(self) -> None:
        self._client.home_button()

    def press_back(self) -> None:
        self._client.back_button()

    def dismiss_keyboard(self) -> None:
        self._client.dismiss_keyboard()

    def get_alert_text(self) -> str:
        return self._client.get_alert_text()

    def accept_alert(self) -> None:
        self._client.accept_alert()

    def dismiss_alert(self) -> None:
        self._client.dismiss_alert()

    def get_element_attribute(self, element_id: str, name: str):
        return self._client.get_element_attribute(element_id, name)

    def get_element_text(self, element_id: str) -> str:
        return self._client.get_element_text(element_id)

    def is_element_displayed(self, element_id: str) -> bool:
        return self._client.is_element_displayed(element_id)

    def is_element_enabled(self, element_id: str) -> bool:
        return self._client.is_element_enabled(element_id)

    def get_element_rect(self, element_id: str) -> dict:
        return self._client.get_element_rect(element_id)

    @property
    def raw(self):
        return self._client
