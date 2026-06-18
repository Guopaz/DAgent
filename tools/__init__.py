"""Tools package — 高层组合工具（Actions），基于 HelloAgents 标准 Tool 协议。

将 100+ 细粒度 WDA 操作封装为 20 个语义化 Tool 类，每个 Tool 直接继承
hello_agents.tools.Tool，实现 run() 和 get_parameters()，无需中间适配层。

目录结构：
    _base.py           — WDABaseTool 共享基类
    perception.py      — 感知工具（2 个）：observe_screen, inspect_element
    interaction.py     — 交互工具（7 个）：tap_by_name, tap_by_xpath, input_text_by_name, ...
    app_lifecycle.py   — 应用工具（3 个）：launch_and_wait, restart_app, check_app_status
    error_handling.py  — 异常处理（4 个）：handle_alert, dismiss_keyboard_if_present, ...
    device_info.py     — 设备工具（4 个）：get_device_summary, press_home_button, ...
"""

from hello_agents.tools import ToolRegistry

from tools.perception import create_perception_tools
from tools.interaction import create_interaction_tools
from tools.app_lifecycle import create_app_lifecycle_tools
from tools.error_handling import create_error_handling_tools
from tools.device_info import create_device_info_tools


def build_tool_registry(wda) -> ToolRegistry:
    """构建标准的 HelloAgents ToolRegistry，注册所有高层 WDA Action 工具。

    每个工具都是 Tool 的子类，直接通过 registry.register_tool() 注册，
    无需 adapter 桥接层。
    """
    registry = ToolRegistry()
    for tool in (
        create_perception_tools(wda)
        + create_interaction_tools(wda)
        + create_app_lifecycle_tools(wda)
        + create_error_handling_tools(wda)
        + create_device_info_tools(wda)
    ):
        registry.register_tool(tool, auto_expand=False)
    return registry


__all__ = ["build_tool_registry", "ToolRegistry"]
