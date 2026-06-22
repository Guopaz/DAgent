"""工具分类 — 区分观察工具和动作工具"""

# 观察类工具：不改变屏幕状态，无需自动刷新
OBSERVATION_TOOLS = {
    "observe_screen",
    "inspect_element",
    "get_device_summary",
    "check_app_status",
}

# 动作类工具：会改变屏幕状态，执行后需要自动刷新
ACTION_TOOLS = {
    "tap_by_name",
    "tap_by_xpath",
    "tap_by_coordinate",
    "input_text_by_name",
    "scroll_to_find_and_tap",
    "swipe_direction",
    "long_press_by_name",
    "launch_and_wait",
    "restart_app",
    "go_back",
    "press_home_button",
    "lock_unlock_device",
    "clear_interrupt",
    "dismiss_keyboard_if_present",
    "wait_seconds",
}

# 混合型工具：根据参数判断是否为动作工具
# key: 工具名, value: (参数名, 动作值集合)
CONDITIONAL_ACTION_TOOLS = {
    "handle_alert": ("action", {"accept", "dismiss", "custom"}),
    "get_tab_bar": ("mode", {"switch"}),
}


def is_action_tool(tool_name: str, arguments: dict = None) -> bool:
    """
    判断是否为动作类工具

    Args:
        tool_name: 工具名称
        arguments: 工具调用参数（用于混合型工具判断）

    Returns:
        True 表示该工具会改变屏幕状态，执行后需要自动刷新
    """
    if tool_name in ACTION_TOOLS:
        return True
    if tool_name in CONDITIONAL_ACTION_TOOLS and arguments:
        param_name, action_values = CONDITIONAL_ACTION_TOOLS[tool_name]
        return arguments.get(param_name) in action_values
    return False
