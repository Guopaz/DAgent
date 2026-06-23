"""工作流工具辅助函数

复用项目中的工具分类逻辑，避免重复定义。
"""


def is_action_tool(tool_name: str, arguments: dict = None) -> bool:
    """判断是否为动作类工具

    直接委托给项目中的 tools.tool_categories.is_action_tool，
    如果不可用则使用内置的简化版本。
    """
    try:
        from tools.tool_categories import is_action_tool as _is_action
        return _is_action(tool_name, arguments)
    except ImportError:
        pass

    # 内置简化版本（当项目 tools 模块不可用时）
    ACTION_TOOLS = {
        "tap_element", "tap_by_coordinate", "input_text",
        "scroll_to_find_and_tap", "swipe_direction", "long_press_by_name",
        "launch_and_wait", "restart_app", "go_back",
        "press_home_button", "lock_unlock_device", "clear_interrupt",
        "dismiss_keyboard_if_present", "wait_seconds", "tap_keyboard_return",
        "wda_call",
    }
    CONDITIONAL_ACTION_TOOLS = {
        "handle_alert": ("action", {"accept", "dismiss", "custom"}),
        "get_tab_bar": ("mode", {"switch"}),
    }
    if tool_name in ACTION_TOOLS:
        return True
    if tool_name in CONDITIONAL_ACTION_TOOLS and arguments:
        param_name, action_values = CONDITIONAL_ACTION_TOOLS[tool_name]
        return arguments.get(param_name) in action_values
    return False
