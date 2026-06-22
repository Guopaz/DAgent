"""通用 WDA 调用工具 — 让 Agent 按需调用 WDA client 的任何方法。"""

from __future__ import annotations

import inspect
from typing import List, Optional

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


# 允许 Agent 调用的 WDA 方法白名单（排除危险操作和已封装为独立工具的方法）
ALLOWED_METHODS = {
    # 截图
    "get_screenshot", "get_element_screenshot",
    # 页面源
    "get_source", "get_accessible_source",
    # 元素查找
    "find_element", "find_elements", "find_element_from_element",
    "find_elements_from_element", "get_active_element", "get_visible_cells",
    # 元素属性
    "get_element_text", "get_element_attribute", "is_element_displayed",
    "is_element_enabled", "is_element_selected", "get_element_name",
    "get_element_rect", "is_element_accessible", "is_element_focused",
    # 元素交互
    "click_element", "click_element_relative", "send_keys",
    "clear_element", "focus_element", "select_pickerwheel",
    # 坐标手势
    "tap", "swipe", "pinch", "rotate", "double_tap", "two_finger_tap",
    "touch_and_hold", "scroll", "drag", "press_and_drag", "force_touch",
    "tap_with_number_of_taps",
    # 元素手势
    "swipe_element", "pinch_element", "rotate_element", "double_tap_element",
    "two_finger_tap_element", "touch_and_hold_element", "scroll_element",
    "scroll_to_element", "drag_element", "press_and_drag_element",
    "force_touch_element", "tap_element", "tap_element_with_number_of_taps",
    # 触摸动作
    "touch_perform", "touch_multi_perform", "w3c_actions",
    # App 管理
    "launch_app", "activate_app", "terminate_app", "get_app_state", "list_apps",
    # 设备控制
    "press_home", "press_button", "deactivate_app",
    "lock_screen", "unlock_screen", "is_locked",
    # 屏幕/设备信息
    "get_screen_info", "get_active_app_info", "get_battery_info",
    "get_device_info", "set_device_appearance",
    "get_device_location", "set_simulated_location", "clear_simulated_location",
    # 方向
    "get_orientation", "set_orientation", "get_rotation", "set_rotation",
    "get_window_size",
    # 弹窗
    "get_alert_text", "set_alert_text", "accept_alert", "dismiss_alert",
    "get_alert_buttons", "alert_action", "clear_alert",
    # 键盘
    "dismiss_keyboard",
    # 剪贴板
    "get_clipboard", "set_clipboard",
    # 全局按键
    "send_global_keys",
    # Siri
    "activate_siri",
    # 无障碍
    "perform_accessibility_audit",
    # Touch ID
    "set_touch_id",
    # App Switcher
    "activate_app_switcher",
    # 设置
    "get_settings", "update_settings",
    # 超时
    "set_timeouts",
    # 重置授权
    "reset_app_auth",
    # HID 事件
    "perform_io_hid_event",
    # 等待
    "wait",
}

# 危险方法（禁止调用）
BLOCKED_METHODS = {
    "create_session", "delete_session", "close",
    "_request", "_get", "_post", "_delete", "_session_path",
}


class WDACallTool(WDABaseTool):
    """通用 WDA 调用工具 — 让 Agent 按需调用 WDA client 的任何方法。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="wda_call",
            description=(
                "通用 WDA 调用工具。可以调用 WDA client 的任何方法，用于处理高级工具未覆盖的场景。\n\n"
                "## 截图\n"
                "- wda_call(method='get_screenshot') → 获取屏幕截图 (base64)\n"
                "- wda_call(method='get_element_screenshot', params={'element_id': 'xxx'}) → 元素截图\n\n"
                "## 页面源\n"
                "- wda_call(method='get_source') → 获取页面 XML 元素树\n"
                "- wda_call(method='get_accessible_source') → 获取可访问性源码\n\n"
                "## 元素查找\n"
                "- wda_call(method='find_element', params={'using': 'name', 'value': '设置'}) → 查找单个元素\n"
                "- wda_call(method='find_elements', params={'using': 'class name', 'value': 'XCUIElementTypeButton'}) → 查找多个元素\n"
                "- wda_call(method='find_element_from_element', params={'element_id': 'xxx', 'using': 'xpath', 'value': './/XCUIElementTypeButton'}) → 从元素查找子元素\n"
                "- wda_call(method='find_elements_from_element', params={'element_id': 'xxx', 'using': 'class name', 'value': 'XCUIElementTypeCell'}) → 从元素查找多个子元素\n"
                "- wda_call(method='get_active_element') → 获取当前活跃/聚焦元素\n"
                "- wda_call(method='get_visible_cells', params={'element_id': 'xxx'}) → 获取可见 Cell\n\n"
                "## 元素属性\n"
                "- wda_call(method='get_element_text', params={'element_id': 'xxx'}) → 获取元素文本\n"
                "- wda_call(method='get_element_attribute', params={'element_id': 'xxx', 'name': 'label'}) → 获取元素属性\n"
                "- wda_call(method='is_element_displayed', params={'element_id': 'xxx'}) → 是否可见\n"
                "- wda_call(method='is_element_enabled', params={'element_id': 'xxx'}) → 是否可用\n"
                "- wda_call(method='is_element_selected', params={'element_id': 'xxx'}) → 是否选中\n"
                "- wda_call(method='get_element_name', params={'element_id': 'xxx'}) → 获取元素类型名\n"
                "- wda_call(method='get_element_rect', params={'element_id': 'xxx'}) → 获取元素位置和尺寸\n"
                "- wda_call(method='is_element_accessible', params={'element_id': 'xxx'}) → 是否可访问\n"
                "- wda_call(method='is_element_focused', params={'element_id': 'xxx'}) → 是否聚焦\n\n"
                "## 元素交互\n"
                "- wda_call(method='click_element', params={'element_id': 'xxx'}) → 点击元素\n"
                "- wda_call(method='click_element_relative', params={'element_id': 'xxx', 'x': 0.5, 'y': 0.5}) → 相对坐标点击\n"
                "- wda_call(method='send_keys', params={'element_id': 'xxx', 'text': 'hello'}) → 输入文本\n"
                "- wda_call(method='clear_element', params={'element_id': 'xxx'}) → 清除文本\n"
                "- wda_call(method='focus_element', params={'element_id': 'xxx'}) → 聚焦元素\n"
                "- wda_call(method='select_pickerwheel', params={'element_id': 'xxx', 'order': 'next', 'offset': 0.2}) → 选择滚轮\n\n"
                "## 坐标手势\n"
                "- wda_call(method='tap', params={'x': 200, 'y': 400}) → 坐标点击\n"
                "- wda_call(method='swipe', params={'direction': 'left', 'velocity': 2000}) → 滑动\n"
                "- wda_call(method='pinch', params={'scale': 0.5, 'velocity': 1.0}) → 缩小\n"
                "- wda_call(method='rotate', params={'rotation': 90, 'velocity': 1.0}) → 旋转\n"
                "- wda_call(method='double_tap', params={'x': 200, 'y': 400}) → 双击\n"
                "- wda_call(method='two_finger_tap', params={'x': 200, 'y': 400}) → 双指点击\n"
                "- wda_call(method='touch_and_hold', params={'x': 200, 'y': 400, 'duration': 2.0}) → 长按\n"
                "- wda_call(method='scroll', params={'direction': 'down', 'distance': '0.5'}) → 滚动\n"
                "- wda_call(method='drag', params={'from_x': 100, 'from_y': 200, 'to_x': 300, 'to_y': 400, 'duration': 1.0}) → 拖拽\n"
                "- wda_call(method='press_and_drag', params={'from_x': 100, 'from_y': 200, 'to_x': 300, 'to_y': 400, 'press_duration': 0.5, 'velocity': 800.0, 'hold_duration': 0.5}) → 按压拖拽\n"
                "- wda_call(method='force_touch', params={'x': 200, 'y': 400, 'pressure': 1.0, 'duration': 1.0}) → 3D Touch\n"
                "- wda_call(method='tap_with_number_of_taps', params={'number_of_taps': 2, 'number_of_touches': 1}) → 多次点击\n\n"
                "## 元素手势\n"
                "- wda_call(method='swipe_element', params={'element_id': 'xxx', 'direction': 'left', 'velocity': 1.0}) → 元素滑动\n"
                "- wda_call(method='pinch_element', params={'element_id': 'xxx', 'scale': 0.5, 'velocity': 1.0}) → 元素捏合\n"
                "- wda_call(method='rotate_element', params={'element_id': 'xxx', 'rotation': 90, 'velocity': 1.0}) → 元素旋转\n"
                "- wda_call(method='double_tap_element', params={'element_id': 'xxx'}) → 元素双击\n"
                "- wda_call(method='two_finger_tap_element', params={'element_id': 'xxx'}) → 元素双指点击\n"
                "- wda_call(method='touch_and_hold_element', params={'element_id': 'xxx', 'duration': 2.0}) → 元素长按\n"
                "- wda_call(method='scroll_element', params={'element_id': 'xxx', 'direction': 'down', 'distance': '1.0'}) → 元素滚动\n"
                "- wda_call(method='scroll_to_element', params={'element_id': 'xxx', 'target_element_id': 'yyy'}) → 滚动到元素\n"
                "- wda_call(method='drag_element', params={'element_id': 'xxx', 'from_x': 0, 'from_y': 0, 'to_x': 100, 'to_y': 100, 'duration': 1.0}) → 元素拖拽\n"
                "- wda_call(method='press_and_drag_element', params={'element_id': 'xxx', 'to_element_id': 'yyy', 'press_duration': 0.5, 'velocity': 800.0, 'hold_duration': 0.5}) → 元素间拖拽\n"
                "- wda_call(method='force_touch_element', params={'element_id': 'xxx', 'pressure': 1.0, 'duration': 1.0}) → 元素 3D Touch\n"
                "- wda_call(method='tap_element', params={'element_id': 'xxx'}) → 元素点击\n"
                "- wda_call(method='tap_element_with_number_of_taps', params={'element_id': 'xxx', 'number_of_taps': 2, 'number_of_touches': 1}) → 元素多次点击\n\n"
                "## 触摸动作\n"
                "- wda_call(method='touch_perform', params={'actions': [{'action': 'press', 'options': {'x': 200, 'y': 500}}, {'action': 'wait', 'options': {'ms': 200}}, {'action': 'moveTo', 'options': {'x': 200, 'y': 100}}, {'action': 'release', 'options': {}}]}) → Appium 触摸序列\n"
                "- wda_call(method='touch_multi_perform', params={'actions': [...]}) → 多点触摸\n"
                "- wda_call(method='w3c_actions', params={'actions': [{'type': 'pointer', 'id': 'finger1', 'parameters': {'pointerType': 'touch'}, 'actions': [{'type': 'pointerMove', 'duration': 0, 'x': 200, 'y': 500, 'origin': 'viewport'}, {'type': 'pointerDown', 'button': 0}, {'type': 'pause', 'duration': 200}, {'type': 'pointerMove', 'duration': 300, 'x': 200, 'y': 100, 'origin': 'viewport'}, {'type': 'pointerUp', 'button': 0}]}]}) → W3C 标准动作\n\n"
                "## App 管理\n"
                "- wda_call(method='launch_app', params={'bundle_id': 'com.apple.mobilesafari'}) → 启动应用\n"
                "- wda_call(method='activate_app', params={'bundle_id': 'com.apple.mobilesafari'}) → 激活应用\n"
                "- wda_call(method='terminate_app', params={'bundle_id': 'com.apple.mobilesafari'}) → 终止应用\n"
                "- wda_call(method='get_app_state', params={'bundle_id': 'com.apple.mobilesafari'}) → 获取应用状态\n"
                "- wda_call(method='list_apps') → 列出已安装应用\n\n"
                "## 设备控制\n"
                "- wda_call(method='press_home') → 按 Home 键\n"
                "- wda_call(method='press_button', params={'button_name': 'volumeUp'}) → 按物理按钮\n"
                "- wda_call(method='deactivate_app', params={'duration': 5.0}) → 切到后台 5 秒\n"
                "- wda_call(method='lock_screen') → 锁屏\n"
                "- wda_call(method='unlock_screen') → 解锁\n"
                "- wda_call(method='is_locked') → 是否锁定\n\n"
                "## 屏幕/设备信息\n"
                "- wda_call(method='get_screen_info') → 获取屏幕信息\n"
                "- wda_call(method='get_active_app_info') → 获取当前应用信息\n"
                "- wda_call(method='get_battery_info') → 获取电池信息\n"
                "- wda_call(method='get_device_info') → 获取设备信息\n"
                "- wda_call(method='set_device_appearance', params={'name': 'dark'}) → 设置外观模式\n"
                "- wda_call(method='get_device_location') → 获取设备位置\n"
                "- wda_call(method='set_simulated_location', params={'latitude': 39.9, 'longitude': 116.4}) → 设置模拟位置\n"
                "- wda_call(method='clear_simulated_location') → 清除模拟位置\n\n"
                "## 方向\n"
                "- wda_call(method='get_orientation') → 获取当前方向\n"
                "- wda_call(method='set_orientation', params={'orientation': 'LANDSCAPE'}) → 设置方向\n"
                "- wda_call(method='get_rotation') → 获取旋转角度\n"
                "- wda_call(method='set_rotation', params={'x': 0, 'y': 0, 'z': 90}) → 设置旋转\n"
                "- wda_call(method='get_window_size') → 获取屏幕尺寸\n\n"
                "## 弹窗\n"
                "- wda_call(method='get_alert_text') → 获取弹窗文本\n"
                "- wda_call(method='set_alert_text', params={'text': 'hello'}) → 设置弹窗文本\n"
                "- wda_call(method='accept_alert') → 接受弹窗\n"
                "- wda_call(method='dismiss_alert') → 关闭弹窗\n"
                "- wda_call(method='get_alert_buttons') → 获取弹窗按钮\n"
                "- wda_call(method='alert_action', params={'action': 'accept'}) → 设置默认弹窗行为\n"
                "- wda_call(method='clear_alert') → 清除弹窗\n\n"
                "## 键盘/剪贴板/按键\n"
                "- wda_call(method='dismiss_keyboard') → 关闭键盘\n"
                "- wda_call(method='get_clipboard') → 获取剪贴板\n"
                "- wda_call(method='set_clipboard', params={'text': 'hello'}) → 设置剪贴板\n"
                "- wda_call(method='send_global_keys', params={'text': 'hello'}) → 全局键盘输入\n\n"
                "## Siri\n"
                "- wda_call(method='activate_siri', params={'text': '打开设置'}) → 激活 Siri\n\n"
                "## 无障碍/Touch ID/App Switcher\n"
                "- wda_call(method='perform_accessibility_audit', params={'audit_types': ['XCUIAccessibilityAuditTypeAll']}) → 无障碍审计\n"
                "- wda_call(method='set_touch_id', params={'match': True}) → 模拟 Touch ID\n"
                "- wda_call(method='activate_app_switcher') → 激活 App Switcher\n\n"
                "## 设置/超时/其他\n"
                "- wda_call(method='get_settings') → 获取设置\n"
                "- wda_call(method='update_settings', params={'settings': {'key': 'value'}}) → 更新设置\n"
                "- wda_call(method='set_timeouts', params={'implicit': 10000, 'page_load': 30000, 'script': 30000}) → 设置超时\n"
                "- wda_call(method='reset_app_auth', params={'resource': 1}) → 重置应用授权\n"
                "- wda_call(method='perform_io_hid_event', params={'page': 12, 'usage': 1, 'duration': 0.1}) → 执行 HID 事件\n"
                "- wda_call(method='wait', params={'seconds': 2.0}) → 等待\n\n"
                "注意：优先使用高层工具（tap_by_name、scroll_to_find_and_tap 等），"
                "仅在高层工具无法满足需求时使用此工具。"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="method",
                type="string",
                description="WDA client 方法名，如 'tap'、'swipe'、'get_window_size' 等",
                required=True,
            ),
            ToolParameter(
                name="params",
                type="object",
                description="方法参数（字典），如 {'x': 200, 'y': 400}。无参数时传空字典 {} 或不传",
                required=False,
                default={},
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        method_name = params["method"]
        method_params = params.get("params", {}) or {}

        # 安全检查
        if method_name in BLOCKED_METHODS:
            return self._fail(f"方法 '{method_name}' 被禁止调用（危险操作）")

        if method_name not in ALLOWED_METHODS:
            return self._fail(
                f"方法 '{method_name}' 不在允许列表中。"
                f"可用方法：{', '.join(sorted(ALLOWED_METHODS)[:20])}... "
                f"（共 {len(ALLOWED_METHODS)} 个）"
            )

        # 检查方法是否存在
        method = getattr(self.wda, method_name, None)
        if method is None:
            return self._fail(f"WDA client 没有方法 '{method_name}'")

        if not callable(method):
            return self._fail(f"'{method_name}' 不是可调用方法")

        # 验证参数匹配
        try:
            sig = inspect.signature(method)
            # 检查必填参数是否都提供了
            for param_name, param in sig.parameters.items():
                if param.default is inspect.Parameter.empty and param_name not in method_params:
                    return self._fail(
                        f"方法 '{method_name}' 缺少必填参数 '{param_name}'。"
                        f"方法签名: {sig}"
                    )
        except (ValueError, TypeError):
            pass  # 无法检查签名时跳过

        # 执行调用
        try:
            result = method(**method_params)
        except TypeError as e:
            # 参数不匹配
            sig = inspect.signature(method)
            return self._fail(f"参数错误: {e}。方法签名: {sig}")
        except Exception as e:
            return self._fail(f"调用 {method_name} 失败: {e}")

        # 格式化返回值
        if result is None:
            return self._ok(f"✅ {method_name} 执行成功")
        return self._ok(f"✅ {method_name} 返回: {result}", data={"result": result})


def create_wda_call_tool(wda) -> list[WDABaseTool]:
    return [WDACallTool(wda)]
