"""Tools package — register all tool modules and re-export public API."""
from tools.executor import ToolExecutor, get_tools, register_tool_module
from tools import perception, element, gesture, app, device, system, knowledge_tools

register_tool_module(perception)
register_tool_module(element)
register_tool_module(gesture)
register_tool_module(app)
register_tool_module(device)
register_tool_module(system)
register_tool_module(knowledge_tools)

__all__ = ["ToolExecutor", "get_tools"]
