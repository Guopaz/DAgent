"""异常处理工具 — 弹窗、键盘、返回导航。"""

from __future__ import annotations

from typing import List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


class HandleAlert(WDABaseTool):
    """智能处理系统弹窗。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="handle_alert",
            description=(
                "智能处理系统弹窗/权限弹窗。\n"
                "- 先读取弹窗内容和可用按钮列表\n"
                "- 'accept'：点击确认按钮（第一个/默认按钮），适用于\u201c允许\u201d\u201c确定\u201d等\n"
                "- 'dismiss'：点击取消按钮，适用于\u201c不允许\u201d\u201c取消\u201d等\n"
                "- 'custom'：点击指定按钮名的按钮（模糊匹配，不区分中英文）\n"
                "使用场景：权限请求弹窗（位置、相机、通知等）、确认对话框\n"
                "示例：handle_alert(action='accept') → 接受弹窗\n"
                "示例：handle_alert(action='custom', button_name='允许') → 点击\u201c允许\u201d按钮"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="处理方式：'accept'（确认，默认）/ 'dismiss'（取消）/ 'custom'（指定按钮名）",
                required=False,
                default="accept",
            ),
            ToolParameter(
                name="button_name",
                type="string",
                description="当 action='custom' 时，指定要点击的按钮名称（支持模糊匹配）",
                required=False,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        action = params.get("action", "accept")
        button_name = params.get("button_name")

        try:
            alert_text = self.wda.get_alert_text()
        except Exception:
            return self._ok("当前无弹窗")
        if not alert_text:
            return self._ok("当前无弹窗")

        try:
            buttons = self.wda.get_alert_buttons()
        except Exception:
            buttons = []

        try:
            if action == "accept":
                self.wda.accept_alert()
                return self._ok(f"✅ 已确认弹窗：{alert_text}")
            elif action == "dismiss":
                self.wda.dismiss_alert()
                return self._ok(f"✅ 已取消弹窗：{alert_text}")
            elif action == "custom" and button_name:
                matched = next((b for b in buttons if button_name.lower() in b.lower()), None)
                if matched:
                    self.wda.alert_action(matched)
                    return self._ok(f"✅ 已点击弹窗按钮：{matched}")
                return self._fail(f"未找到按钮 '{button_name}'，可用按钮：{buttons}")
            else:
                return self._ok(f"弹窗内容：{alert_text}\n可用按钮：{buttons}")
        except Exception as exc:
            return self._fail(f"处理弹窗失败（{exc}），弹窗内容：{alert_text}，按钮：{buttons}")


class DismissKeyboardIfPresent(WDABaseTool):
    """如果键盘可见则关闭。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="dismiss_keyboard_if_present",
            description=(
                "如果键盘可见则关闭键盘。\n"
                "- 如果当前没有键盘，返回\u201c当前无键盘\u201d而不是报错\n"
                "使用场景：输入文本后确保键盘已关闭，方便点击下方元素\n"
                "示例：dismiss_keyboard_if_present()"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        try:
            self.wda.dismiss_keyboard()
            return self._ok("✅ 已关闭键盘")
        except Exception:
            return self._ok("当前无键盘")


class ClearInterrupt(WDABaseTool):
    """一键清除所有中断。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="clear_interrupt",
            description=(
                "一键清除所有中断（弹窗 + 键盘），恢复到干净的交互状态。\n"
                "- 自动尝试关闭弹窗和键盘，单个操作失败不影响其他\n"
                "- 全部清除后返回清除结果列表\n"
                "使用场景：操作前清理状态、弹窗挡住目标元素时\n"
                "示例：clear_interrupt() → '已关闭弹窗、已关闭键盘'"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        results: list[str] = []
        try:
            self.wda.dismiss_alert()
            results.append("已关闭弹窗")
        except Exception:
            pass
        try:
            self.wda.dismiss_keyboard()
            results.append("已关闭键盘")
        except Exception:
            pass
        return self._ok("、".join(results) if results else "当前无中断")


class GoBack(WDABaseTool):
    """智能返回上一页。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="go_back",
            description=(
                "返回到上一页。自动尝试多种方式：\n"
                "- 优先点击左上角的\u201c返回\u201d按钮\n"
                "- 如果找不到，回退到从屏幕左边缘向右滑动（模拟 iOS 返回手势）\n"
                "使用场景：导航返回\n"
                "示例：go_back() → 自动返回上一页"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        # 策略 1: 查找常见的返回按钮
        for back_name in ("返回", "image_返回", "Back", "back", "后退"):
            element_id = self.wda.find_element("name", back_name)
            if element_id and self._is_visible(element_id):
                try:
                    self.wda.click_element(element_id)
                    self.wda.wait(1.0)
                    return self._ok(f"✅ 已点击返回按钮：'{back_name}'")
                except Exception:
                    pass

        # 策略 2: 从屏幕左边缘向右滑动（iOS 返回手势）
        try:
            size = self.wda.get_window_size()
            width = int(size.get("width", 375))
            height = int(size.get("height", 667))
            print(f"屏幕尺寸：{width}x{height}")
            # 从左边缘 (x≈1) 向右滑动约 80% 屏幕宽度，y 在屏幕中间
            from_x = 1
            to_x = int(width * 0.8)
            mid_y = int(height / 2)
            self.wda.drag(from_x, mid_y, to_x, mid_y, duration=0.1)
            self.wda.wait(0.3)
            return self._ok("✅ 已从左边缘滑动返回")
        except Exception:
            return self._fail("无法返回：未找到返回按钮，左边缘滑动也失败")


def create_error_handling_tools(wda) -> list[WDABaseTool]:
    return [HandleAlert(wda), DismissKeyboardIfPresent(wda), ClearInterrupt(wda), GoBack(wda)]
