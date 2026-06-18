"""设备信息工具 — 设备概要、Home 键、锁屏、等待。"""

from __future__ import annotations

from typing import Any, List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


class GetDeviceSummary(WDABaseTool):
    """获取设备概要信息。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="get_device_summary",
            description=(
                "获取设备概要信息，包括型号、系统版本、电量、屏幕尺寸。\n"
                "使用场景：任务开始时了解设备状态\n"
                "示例：get_device_summary() → {'device': {...}, 'battery': {...}, 'screen': {...}}"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        summary: dict[str, Any] = {}
        try:
            summary["device"] = self.wda.get_device_info()
        except Exception:
            summary["device"] = "N/A"
        try:
            summary["battery"] = self.wda.get_battery_info()
        except Exception:
            summary["battery"] = "N/A"
        try:
            summary["screen"] = self.wda.get_screen_info()
        except Exception:
            summary["screen"] = "N/A"
        return self._ok(str(summary), summary)


class PressHomeButton(WDABaseTool):
    """按 Home 键。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="press_home_button",
            description=(
                "按 Home 键回到主屏幕。\n"
                "使用场景：回到桌面、退出当前 App\n"
                "示例：press_home_button()"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        self.wda.press_home()
        return self._ok("✅ 已按 Home 键")


class LockUnlockDevice(WDABaseTool):
    """锁屏或解锁。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="lock_unlock_device",
            description=(
                "锁屏或解锁设备。\n"
                "使用场景：测试锁屏通知、App 后台行为\n"
                "示例：lock_unlock_device(action='lock') → 锁屏\n"
                "示例：lock_unlock_device(action='unlock') → 解锁"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="'lock' 或 'unlock'",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        action = params["action"]
        if action == "lock":
            self.wda.lock_screen()
            return self._ok("✅ 已锁屏")
        else:
            self.wda.unlock_screen()
            return self._ok("✅ 已解锁")


class WaitSeconds(WDABaseTool):
    """等待指定秒数。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="wait_seconds",
            description=(
                "等待指定秒数（最大 10 秒）。\n"
                "使用场景：等待动画完成、网络请求返回、页面加载\n"
                "示例：wait_seconds(seconds=3) → 等待 3 秒"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="seconds",
                type="number",
                description="等待秒数，范围 0.1-10",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        seconds = min(max(float(params["seconds"]), 0.1), 10.0)
        self.wda.wait(seconds)
        return self._ok(f"✅ 已等待 {seconds} 秒")


def create_device_info_tools(wda) -> list[WDABaseTool]:
    return [GetDeviceSummary(wda), PressHomeButton(wda), LockUnlockDevice(wda), WaitSeconds(wda)]
