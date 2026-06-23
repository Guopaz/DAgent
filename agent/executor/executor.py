"""执行器 — 将抽象动作翻译为 WDA 命令。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, Optional

from agent.models import Action, ActionRecord, ActionType, ToolResponse

if TYPE_CHECKING:
    from agent.wda.client import WDAClient


class Executor:
    """执行器 — 执行 Planner 输出的动作。"""

    def __init__(self, wda: WDAClient):
        self.wda = wda

    def execute(self, action: Action) -> ActionRecord:
        """执行动作并返回记录。"""
        start_time = time.time()
        
        try:
            result = self._dispatch(action)
        except Exception as e:
            result = ToolResponse(success=False, message=str(e))

        duration = time.time() - start_time
        
        record = ActionRecord(
            tool_name=action.action_type.value,
            parameters={"target": action.target, **action.parameters},
            result=result,
            timestamp=start_time,
            duration=duration,
        )

        return record

    def _dispatch(self, action: Action) -> ToolResponse:
        """根据动作类型分发到具体执行函数。"""
        dispatch_map = {
            ActionType.CLICK: self._execute_click,
            ActionType.INPUT: self._execute_input,
            ActionType.SCROLL: self._execute_scroll,
            ActionType.SWIPE: self._execute_swipe,
            ActionType.WAIT: self._execute_wait,
            ActionType.BACK: self._execute_back,
            ActionType.HOME: self._execute_home,
            ActionType.LAUNCH_APP: self._execute_launch_app,
            ActionType.DISMISS_ALERT: self._execute_dismiss_alert,
            ActionType.DISMISS_KEYBOARD: self._execute_dismiss_keyboard,
            ActionType.LONG_PRESS: self._execute_long_press,
            ActionType.NONE: self._execute_none,
        }

        handler = dispatch_map.get(action.action_type)
        if handler is None:
            return ToolResponse(success=False, message=f"未知的动作类型: {action.action_type}")

        return handler(action)

    def _execute_click(self, action: Action) -> ToolResponse:
        """执行点击动作。"""
        target = action.target
        if not target:
            return ToolResponse(success=False, message="点击动作缺少目标元素")

        element_id = self.wda.find_element("name", target)
        if not element_id:
            return ToolResponse(success=False, message=f"未找到元素: {target}")

        try:
            self.wda.tap_element(element_id)
            return ToolResponse(success=True, message=f"成功点击: {target}")
        except Exception as e:
            return ToolResponse(success=False, message=f"点击失败: {e}")

    def _execute_input(self, action: Action) -> ToolResponse:
        """执行输入动作。"""
        target = action.target
        text = action.parameters.get("text", "")
        
        if not target:
            return ToolResponse(success=False, message="输入动作缺少目标元素")
        if not text:
            return ToolResponse(success=False, message="输入动作缺少文本")

        element_id = self.wda.find_element("name", target)
        if not element_id:
            return ToolResponse(success=False, message=f"未找到元素: {target}")

        try:
            self.wda.type_text(element_id, text)
            return ToolResponse(success=True, message=f"成功输入 '{text}' 到 {target}")
        except Exception as e:
            return ToolResponse(success=False, message=f"输入失败: {e}")

    def _execute_scroll(self, action: Action) -> ToolResponse:
        """执行滚动动作。"""
        direction = action.parameters.get("direction", "down")
        
        try:
            self.wda.scroll(direction)
            return ToolResponse(success=True, message=f"成功滚动: {direction}")
        except Exception as e:
            return ToolResponse(success=False, message=f"滚动失败: {e}")

    def _execute_swipe(self, action: Action) -> ToolResponse:
        """执行滑动手势。"""
        from_x = action.parameters.get("from_x", 200)
        from_y = action.parameters.get("from_y", 400)
        to_x = action.parameters.get("to_x", 200)
        to_y = action.parameters.get("to_y", 200)
        duration = action.parameters.get("duration", 0.5)

        try:
            self.wda.swipe(from_x, from_y, to_x, to_y, duration)
            return ToolResponse(success=True, message=f"成功滑动: ({from_x},{from_y}) → ({to_x},{to_y})")
        except Exception as e:
            return ToolResponse(success=False, message=f"滑动失败: {e}")

    def _execute_wait(self, action: Action) -> ToolResponse:
        """执行等待动作。"""
        seconds = action.parameters.get("seconds", 2)
        time.sleep(seconds)
        return ToolResponse(success=True, message=f"等待 {seconds} 秒")

    def _execute_back(self, action: Action) -> ToolResponse:
        """执行返回动作。"""
        try:
            self.wda.press_back()
            return ToolResponse(success=True, message="成功返回")
        except Exception as e:
            return ToolResponse(success=False, message=f"返回失败: {e}")

    def _execute_home(self, action: Action) -> ToolResponse:
        """执行回到主屏幕动作。"""
        try:
            self.wda.go_home()
            return ToolResponse(success=True, message="成功回到主屏幕")
        except Exception as e:
            return ToolResponse(success=False, message=f"回到主屏幕失败: {e}")

    def _execute_launch_app(self, action: Action) -> ToolResponse:
        """执行启动应用动作。"""
        bundle_id = action.parameters.get("bundle_id", "")
        if not bundle_id:
            return ToolResponse(success=False, message="启动应用缺少 bundle_id")

        try:
            self.wda.launch_app(bundle_id)
            time.sleep(2)
            return ToolResponse(success=True, message=f"成功启动应用: {bundle_id}")
        except Exception as e:
            return ToolResponse(success=False, message=f"启动应用失败: {e}")

    def _execute_dismiss_alert(self, action: Action) -> ToolResponse:
        """执行关闭弹窗动作。"""
        try:
            self.wda.dismiss_alert()
            return ToolResponse(success=True, message="成功关闭弹窗")
        except Exception as e:
            return ToolResponse(success=False, message=f"关闭弹窗失败: {e}")

    def _execute_dismiss_keyboard(self, action: Action) -> ToolResponse:
        """执行关闭键盘动作。"""
        try:
            self.wda.dismiss_keyboard()
            return ToolResponse(success=True, message="成功关闭键盘")
        except Exception as e:
            return ToolResponse(success=False, message=f"关闭键盘失败: {e}")

    def _execute_long_press(self, action: Action) -> ToolResponse:
        """执行长按动作。"""
        target = action.target
        duration = action.parameters.get("duration", 2.0)
        
        if not target:
            return ToolResponse(success=False, message="长按动作缺少目标元素")

        element_id = self.wda.find_element("name", target)
        if not element_id:
            return ToolResponse(success=False, message=f"未找到元素: {target}")

        try:
            rect = self.wda.get_element_rect(element_id)
            x = rect.get("x", 0) + rect.get("width", 0) / 2
            y = rect.get("y", 0) + rect.get("height", 0) / 2
            self.wda.tap(x, y)
            return ToolResponse(success=True, message=f"成功长按: {target}")
        except Exception as e:
            return ToolResponse(success=False, message=f"长按失败: {e}")

    def _execute_none(self, action: Action) -> ToolResponse:
        """执行无操作。"""
        return ToolResponse(success=True, message="无操作")
