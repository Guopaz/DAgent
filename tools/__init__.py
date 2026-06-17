"""Tools package — build HelloAgents ToolRegistry from WDA tool modules."""
from hello_agents.tools import ToolRegistry
from tools.adapter import build_wda_tools
from tools import perception, element, gesture, app, device, system

ALL_TOOL_MODULES = [perception, element, gesture, app, device, system]


def build_tool_registry(wda) -> ToolRegistry:
    """Build a HelloAgents ToolRegistry with all WDA tools registered."""
    registry = ToolRegistry()
    for tool in build_wda_tools(wda, tool_modules=ALL_TOOL_MODULES):
        registry.register_tool(tool, auto_expand=False)
    return registry


__all__ = ["build_tool_registry", "ToolRegistry"]
