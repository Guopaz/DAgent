"""应用生命周期工具 — 启动、重启和检查 App 运行状态。"""

from __future__ import annotations

from typing import List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


_STATE_MAP = {0: "未安装", 1: "未运行", 2: "后台", 3: "挂起", 4: "前台"}


class LaunchAndWait(WDABaseTool):
    """启动 App 并等待首页加载。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="launch_and_wait",
            description=(
                "启动 App 并等待首页加载完成，返回首页元素摘要。\n"
                "- 启动后等待 2 秒让 App 完成启动动画\n"
                "- 自动获取首页 UI 元素树的前 2000 字符，方便直接判断下一步操作\n"
                "使用场景：任务开始时启动目标 App\n"
                "示例：launch_and_wait(bundle_id='com.apple.Preferences') → 启动设置 App 并返回首页摘要"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="bundle_id",
                type="string",
                description="App 的 Bundle ID，如 com.apple.Preferences",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        bundle_id = params["bundle_id"]
        try:
            self.wda.launch_app(bundle_id)
        except Exception as exc:
            return self._fail(f"启动失败：{bundle_id}（{exc}），请检查 bundle_id 是否正确")

        self.wda.wait(2)
        try:
            source = self.wda.get_source()
        except Exception:
            return self._fail(f"App 已启动：{bundle_id}，但无法获取首页信息（WDA 会话可能丢失）")

        if len(source) > 2000:
            return self._ok(f"✅ App 已启动：{bundle_id}\n首页元素摘要：{source[:2000]}...")
        return self._ok(f"✅ App 已启动：{bundle_id}\n首页元素：{source}")


class RestartApp(WDABaseTool):
    """重启 App。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="restart_app",
            description=(
                "重启 App（杀死进程 → 等待 1 秒 → 重新启动 → 等待 2 秒）。\n"
                "使用场景：App 无响应、页面卡死、需要重新登录\n"
                "示例：restart_app(bundle_id='com.apple.Preferences')"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="bundle_id", type="string", description="App 的 Bundle ID", required=True),
        ]

    def run(self, params: dict) -> ToolResponse:
        bundle_id = params["bundle_id"]
        try:
            self.wda.kill_app(bundle_id)
        except Exception:
            pass
        self.wda.wait(1.0)
        try:
            self.wda.launch_app(bundle_id)
        except Exception as exc:
            return self._fail(f"重启失败：{bundle_id}（{exc}）")
        self.wda.wait(2)
        return self._ok(f"✅ App 已重启：{bundle_id}")


class CheckAppStatus(WDABaseTool):
    """检查 App 运行状态。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="check_app_status",
            description=(
                "检查 App 的当前运行状态。\n"
                "- 返回状态值：0=未安装、1=未运行、2=后台、3=挂起、4=前台\n"
                "使用场景：确认 App 是否在前台运行，必要时重启\n"
                "示例：check_app_status(bundle_id='com.apple.Preferences') → {'state': 4, 'description': '前台'}"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="bundle_id", type="string", description="App 的 Bundle ID", required=True),
        ]

    def run(self, params: dict) -> ToolResponse:
        bundle_id = params["bundle_id"]
        try:
            state = self.wda.get_app_state(bundle_id)
        except Exception:
            state = -1
        desc = _STATE_MAP.get(state, "未知状态" if state >= 0 else "查询失败")
        return self._ok(f"App {bundle_id} 状态：{desc}", {"bundle_id": bundle_id, "state": state, "description": desc})


def create_app_lifecycle_tools(wda) -> list[WDABaseTool]:
    return [LaunchAndWait(wda), RestartApp(wda), CheckAppStatus(wda)]
