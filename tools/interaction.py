"""交互工具 — 最核心的操作工具集：点击、输入、滚动、滑动、长按。"""

from __future__ import annotations

from typing import List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


class TapByName(WDABaseTool):
    """通过元素名称点击（最常用操作）。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="tap_by_name",
            description=(
                "通过元素名称点击。这是最常用的操作工具。\n"
                "- 自动定位元素（使用 name 策略）\n"
                "- 点击前检查元素是否可见，不可见时返回明确的失败信息\n"
                "- 点击后自动等待 1 秒，等待 UI 过渡完成\n"
                "使用场景：点击按钮、开关、菜单项等任何有 label/name 的元素\n"
                "示例：tap_by_name(name='设置') → 点击\u201c设置\u201d元素\n"
                "示例：tap_by_name(name='Wi-Fi') → 点击 Wi-Fi 开关\n"
                "注意：如果元素不可见（在屏幕外），请使用 scroll_to_find_and_tap"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="元素的 label 或 name，从 observe_screen 返回的 XML 中获取",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params["name"]
        element_id = self._find_by_name(name)
        if not element_id:
            return self._fail(
                f"未找到元素：'{name}'，请先用 observe_screen 确认元素名称"
            )
        if not self._is_visible(element_id):
            return self._fail(
                f"元素 '{name}' 在 DOM 中存在但当前不可见（可能在屏幕外或被遮挡），"
                "建议使用 scroll_to_find_and_tap 或先 clear_interrupt"
            )
        try:
            self.wda.click_element(element_id)
            self.wda.wait(1.0)
            return self._ok(f"✅ 已点击：{name}")
        except Exception as exc:
            return self._fail(f"点击失败：{name}（{exc}），建议 observe_screen 确认页面状态后重试")


class TapByXPath(WDABaseTool):
    """通过 XPath 点击元素。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="tap_by_xpath",
            description=(
                "通过 XPath 表达式点击元素。\n"
                "- 适用于 name 定位不到的复杂场景\n"
                "- 点击前检查元素是否可见\n"
                "- 点击后自动等待 1 秒\n"
                "⚠️ 注意：XPath 依赖 UI 结构，App 更新后可能变化，优先使用 tap_by_name\n"
                "使用场景：元素没有明确的 name/label，或需要按类型+位置定位\n"
                "示例：tap_by_xpath(xpath='//XCUIElementTypeButton[@name=\"确认\"]')\n"
                "示例：tap_by_xpath(xpath='//XCUIElementTypeCell[3]//XCUIElementTypeButton[1]')"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="xpath",
                type="string",
                description="XPath 定位表达式",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        xpath = params["xpath"]
        element_id = self.wda.find_element("xpath", xpath)
        if not element_id:
            return self._fail(f"未找到匹配 XPath 的元素：{xpath}")
        if not self._is_visible(element_id):
            return self._fail(f"XPath 匹配到元素但不可见：{xpath}")
        try:
            self.wda.click_element(element_id)
            self.wda.wait(1.0)
            return self._ok(f"✅ 已点击 XPath：{xpath}")
        except Exception as exc:
            return self._fail(f"点击失败：{xpath}（{exc}）")


class InputTextByName(WDABaseTool):
    """通过名称定位输入框并输入文本。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="input_text_by_name",
            description=(
                "在指定输入框中输入文本。\n"
                "- 定位输入框后先点击聚焦（确保 keyboard 弹出且输入目标正确）\n"
                "- 点击后等待 0.3 秒，再清空已有内容，再输入新文本\n"
                "- 输入完成后自动关闭键盘\n"
                "使用场景：在搜索框、登录表单、设置项中输入文字\n"
                "示例：input_text_by_name(name='搜索', text='WiFi 密码')\n"
                "示例：input_text_by_name(name='Apple ID', text='user@example.com')"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="name", type="string", description="输入框的 label 或 name", required=True),
            ToolParameter(name="text", type="string", description="要输入的文本内容", required=True),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params["name"]
        text = params["text"]

        element_id = self._find_by_name(name)
        if not element_id:
            return self._fail(f"未找到输入框：'{name}'，请先用 observe_screen 确认")

        # 步骤 1: 点击聚焦
        try:
            self.wda.click_element(element_id)
            self.wda.wait(0.3)
        except Exception as exc:
            return self._fail(f"点击输入框失败：{name}（{exc}）")

        # 步骤 2: 清空已有内容
        try:
            self.wda.clear_element(element_id)
            self.wda.wait(0.1)
        except Exception:
            try:
                self.wda.send_keys(element_id, "")
            except Exception:
                pass  # 清空失败不阻塞

        # 步骤 3: 输入文本
        try:
            self.wda.send_keys(element_id, text)
        except Exception as exc:
            return self._fail(f"输入文本失败：{name}（{exc}）")

        # 步骤 4: 关闭键盘
        try:
            self.wda.dismiss_keyboard()
        except Exception:
            pass

        return self._ok(f"✅ 已在 '{name}' 输入：{text}")


class ScrollToFindAndTap(WDABaseTool):
    """滚动查找目标元素并点击。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="scroll_to_find_and_tap",
            description=(
                "滚动查找目标元素，找到后自动点击。适用于元素在屏幕外的长列表页面。\n"
                "- 先尝试直接定位，如果可见就直接点击（不滚动）\n"
                "- 自动识别可滚动容器（TableView/CollectionView），优先在容器内滚动\n"
                "- 没有找到容器时回退到全局坐标滚动\n"
                "- 每次滚动后刷新 DOM 再查找（避免获取到过期的元素树）\n"
                "使用场景：设置列表、通讯录、文件列表等需要滚动才能看到全部内容的页面\n"
                "示例：scroll_to_find_and_tap(name='关于本机') → 向下滚动直到找到并点击\n"
                "示例：scroll_to_find_and_tap(name='退出登录', direction='down', max_scrolls=10)"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="name", type="string", description="目标元素的 label 或 name", required=True),
            ToolParameter(
                name="direction",
                type="string",
                description="滚动方向：'up' / 'down'（默认） / 'left' / 'right'",
                required=False,
                default="down",
            ),
            ToolParameter(
                name="max_scrolls",
                type="integer",
                description="最大滚动次数，默认 5，范围 1-20",
                required=False,
                default=5,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params["name"]
        direction = params.get("direction", "down")
        max_scrolls = min(max(int(params.get("max_scrolls", 5)), 1), 20)

        # Step 1: 直接查找
        element_id = self._find_by_name(name)
        if element_id and self._is_visible(element_id):
            try:
                self.wda.click_element(element_id)
                self.wda.wait(1.0)
                return self._ok(f"✅ 直接找到并点击：{name}（无需滚动）")
            except Exception as exc:
                return self._fail(f"点击失败：{name}（{exc}）")

        # Step 2: 滚动查找
        scrollables = self._find_scrollable_containers()

        for i in range(max_scrolls):
            if scrollables:
                for cid in scrollables:
                    try:
                        self.wda.scroll_element(cid, direction, 0.5)
                    except Exception:
                        continue
            else:
                try:
                    self.wda.scroll(direction, 0.5)
                except Exception:
                    pass

            self.wda.wait(0.5)

            # 刷新 DOM
            try:
                self.wda.get_source()
            except Exception:
                pass

            element_id = self._find_by_name(name)
            if element_id and self._is_visible(element_id):
                try:
                    self.wda.click_element(element_id)
                    self.wda.wait(1.0)
                    return self._ok(f"✅ 找到并点击：{name}（滚动了 {i + 1} 次）")
                except Exception:
                    pass

        return self._fail(
            f"未找到元素：'{name}'（已滚动 {max_scrolls} 次），"
            "建议 observe_screen 确认元素是否存在或调整滚动方向"
        )


class SwipeDirection(WDABaseTool):
    """按方向滑动屏幕。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="swipe_direction",
            description=(
                "按方向滑动屏幕。适用于页面切换、返回上一页等场景。\n"
                "- 'up'：从下往上滑\n"
                "- 'down'：从上往下滑\n"
                "- 'left'：从右往左滑（返回上一页的手势）\n"
                "- 'right'：从左往右滑\n"
                "使用场景：翻页、返回、切换 Tab\n"
                "示例：swipe_direction(direction='left') → 左滑返回上一页\n"
                "示例：swipe_direction(direction='up') → 向上滑动查看更多内容"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="direction",
                type="string",
                description="滑动方向：'up' / 'down' / 'left' / 'right'",
                required=True,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        direction = params["direction"]
        self.wda.scroll(direction, 0.5)
        return self._ok(f"✅ 已向 {direction} 滑动")


class LongPressByName(WDABaseTool):
    """长按指定元素。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="long_press_by_name",
            description=(
                "长按指定元素 2 秒。\n"
                "使用场景：触发上下文菜单（删除、编辑、移动等）、进入图标编辑模式\n"
                "示例：long_press_by_name(name='Safari') → 长按 Safari 图标弹出菜单"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="name", type="string", description="元素的 label 或 name", required=True),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params["name"]
        element_id = self._find_by_name(name)
        if not element_id:
            return self._fail(f"未找到元素：'{name}'")
        try:
            self.wda.touch_and_hold_element(element_id, 2.0)
            return self._ok(f"✅ 已长按：{name}")
        except Exception as exc:
            return self._fail(f"长按失败：{name}（{exc}）")


class TapByCoordinate(WDABaseTool):
    """按屏幕坐标点击（兜底方案）。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="tap_by_coordinate",
            description=(
                "按屏幕坐标点击。适用于无法通过 name/xpath 定位元素的场景（如游戏、地图）。\n"
                "使用场景：点击图片识别的位置、地图上的标记点\n"
                "示例：tap_by_coordinate(x=200, y=400) → 点击坐标 (200, 400)\n"
                "⚠️ 注意：优先使用 tap_by_name，坐标点击仅在没有更好选择时使用"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="x", type="number", description="X 坐标（像素）", required=True),
            ToolParameter(name="y", type="number", description="Y 坐标（像素）", required=True),
        ]

    def run(self, params: dict) -> ToolResponse:
        try:
            x, y = int(params["x"]), int(params["y"])
            self.wda.tap(x, y)
            self.wda.wait(0.5)
            return self._ok(f"✅ 已点击坐标 ({x}, {y})")
        except Exception as exc:
            return self._fail(f"坐标点击失败 ({params['x']}, {params['y']}): {exc}")


def create_interaction_tools(wda) -> list[WDABaseTool]:
    return [
        TapByName(wda),
        TapByXPath(wda),
        InputTextByName(wda),
        ScrollToFindAndTap(wda),
        SwipeDirection(wda),
        LongPressByName(wda),
        TapByCoordinate(wda),
    ]
