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
        
        if direction not in ("up", "down", "left", "right"):
            return self._fail(f"不支持的方向: {direction}，请使用 up/down/left/right")
        
        # 使用 /wda/swipe API（direction + velocity 格式）
        # velocity=2000 像素/秒，足够快以避免触发长按
        self.wda.swipe(direction, velocity=2000)
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


class GetTabBar(WDABaseTool):
    """定位当前页面底部 TabBar，列出 Tab 或切换 Tab。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="get_tab_bar",
            description=(
                "定位当前页面底部 TabBar，列出所有 Tab 或切换 Tab。\n"
                "- action='list'（默认）：返回结构化 Tab 列表（索引、名称、位置）\n"
                "- action='switch'：切换到指定 Tab（按 index 或 tab_name）\n"
                "- 纯图标 Tab 仍返回索引，支持按位置点击\n"
                "- 不受 observe_screen XML 截断影响（精准 XPath 定位底部）\n"
                "使用场景：多 Tab App（微信、淘宝、Boss直聘等）的导航\n"
                "示例：get_tab_bar(action='list') → 列出所有 Tab\n"
                "示例：get_tab_bar(action='switch', index=4) → 切换到第 5 个 Tab\n"
                "示例：get_tab_bar(action='switch', tab_name='我的') → 按名称切换"
            ),
        )
        self._cached = None  # 缓存: {items, tabs, selected_idx, selected_name}

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="action", type="string",
                description="'list'（默认）/ 'switch'（切换）", required=False, default="list"),
            ToolParameter(name="index", type="integer",
                description="action='switch' 时按索引切换（0-based）", required=False),
            ToolParameter(name="tab_name", type="string",
                description="action='switch' 时按名称模糊匹配（不区分大小写）", required=False),
        ]

    def _find_tabbar(self) -> str | None:
        bars = self.wda.find_elements("class name", "XCUIElementTypeTabBar")
        return bars[0] if bars else None

    def _get_tab_items(self, tabbar_id: str) -> list[tuple[str, str]]:
        """快速提取 TabBar 直接子元素的文本（只查自身属性，不做深度遍历）。"""
        try:
            children = self.wda.find_elements_from_element(tabbar_id, "xpath", "./*")
        except Exception:
            return []

        items = []
        for child_id in children:
            etype = self._safe_get_attr(child_id, "type", "")
            if etype == "XCUIElementTypeImage":
                continue

            raw_label = self._safe_get_attr(child_id, "label", "").strip()
            raw_name = self._safe_get_attr(child_id, "name", "").strip()

            if raw_label:
                # 复合标签: "招人, SPTabBar_Boss_zhaoren" → "招人"
                text = raw_label.split(",")[0].strip()
                if text and not text.isdigit():
                    items.append((child_id, text))
                    continue
            if raw_name and not raw_name.startswith("button_") and not raw_name.isdigit():
                items.append((child_id, raw_name))
                continue

        # 回退：直接子元素无文本时，只取 Button
        if not items:
            try:
                buttons = self.wda.find_elements_from_element(tabbar_id, "class name", "XCUIElementTypeButton")
            except Exception:
                buttons = []
            for btn_id in buttons:
                label = self._safe_get_attr(btn_id, "label", "").strip()
                name = self._safe_get_attr(btn_id, "name", "").strip()
                text = label or name
                if text and not text.isdigit():
                    items.append((btn_id, text))
        return items

    def _is_selected(self, element_id: str) -> bool:
        try:
            if self.wda.is_element_selected(element_id):
                return True
        except Exception:
            pass
        try:
            if self.wda.get_element_attribute(element_id, "value") == "1":
                return True
        except Exception:
            pass
        try:
            if self.wda.get_element_attribute(element_id, "selected") == "true":
                return True
        except Exception:
            pass
        return False

    def _build_tab_info(self, items: list[tuple[str, str]]) -> tuple[list[dict], int, str]:
        """构建 Tab 列表，返回 (tabs, selected_idx, selected_name)。"""
        tabs = []
        sel_idx, sel_name = -1, ""
        for i, (eid, display) in enumerate(items):
            tabs.append({"index": i, "screen_name": display})
            if self._is_selected(eid):
                sel_idx, sel_name = i, display
        if sel_idx == -1 and tabs:
            sel_idx, sel_name = 0, tabs[0]["screen_name"]
        return tabs, sel_idx, sel_name

    def _discover(self):
        """发现 TabBar 并缓存结果（idempotent）。"""
        if self._cached is not None:
            return  # 已有缓存
        tabbar_id = self._find_tabbar()
        if not tabbar_id:
            self._cached = False  # 标记为无 TabBar
            return
        items = self._get_tab_items(tabbar_id)
        if not items:
            self._cached = False
            return
        tabs, sel_idx, sel_name = self._build_tab_info(items)
        self._cached = {"element_ids": [eid for eid, _ in items],
                        "tabs": tabs,
                        "selected_index": sel_idx,
                        "selected_name": sel_name}

    def run(self, params: dict) -> ToolResponse:
        action = params.get("action", "list")
        index = params.get("index")
        tab_name = params.get("tab_name")

        if action == "switch":
            if index is not None and tab_name is not None:
                return self._fail("请只提供 index 或 tab_name 之一")
            if index is None and tab_name is None:
                return self._fail("action='switch' 时请提供 index 或 tab_name")

        self._discover()
        if self._cached is None or self._cached is False:
            return self._ok(str({"found": False, "tab_count": 0, "selected_index": -1,
                "selected_name": "", "tabs": [], "reason": "当前页面未检测到 TabBar 或无法提取标签"}),
                {"found": False, "tab_count": 0, "selected_index": -1, "selected_name": "", "tabs": [],
                 "reason": "当前页面未检测到 TabBar 或无法提取标签"})

        c = self._cached
        if action == "list":
            data = {"found": True, "tab_count": len(c["tabs"]),
                    "selected_index": c["selected_index"], "selected_name": c["selected_name"],
                    "tabs": c["tabs"]}
            return self._ok(str(data), data)

        # action="switch"
        target_idx = None
        elem_to_click = None
        if tab_name is not None:
            matches = []
            for i, eid in enumerate(c["element_ids"]):
                display = c["tabs"][i]["screen_name"]
                if tab_name.lower() == display.lower():
                    matches.insert(0, {"index": i, "element_id": eid, "name": display})
                elif tab_name.lower() in display.lower():
                    matches.append({"index": i, "element_id": eid, "name": display})
            if not matches:
                names = [t["screen_name"] for t in c["tabs"]]
                return self._fail(f"未找到匹配 '{tab_name}' 的 Tab，可用: {names}")
            if len(matches) > 1:
                return self._fail(f"'{tab_name}' 匹配到多个 Tab: {[(m['index'],m['name']) for m in matches]}，请用 index")
            target_idx = matches[0]["index"]
            elem_to_click = matches[0]["element_id"]
        elif index is not None:
            if index < 0 or index >= len(c["element_ids"]):
                return self._fail(f"索引 {index} 超出范围，有效: 0-{len(c['element_ids'])-1}")
            target_idx = index
            elem_to_click = c["element_ids"][index]

        if elem_to_click is None:
            return self._fail("无法定位目标按钮")
        try:
            self.wda.click_element(elem_to_click)
            self.wda.wait(0.5)
            # 切换后清缓存，下次 list 会重新发现
            self._cached = None
            return self._ok(f"\u2705 已切换到 Tab [{target_idx}] {c['tabs'][target_idx]['screen_name']}")
        except Exception as exc:
            return self._fail(f"切换 Tab [{target_idx}] 失败: {exc}")


def create_interaction_tools(wda) -> list[WDABaseTool]:
    return [
        TapByName(wda),
        TapByXPath(wda),
        InputTextByName(wda),
        ScrollToFindAndTap(wda),
        SwipeDirection(wda),
        LongPressByName(wda),
        TapByCoordinate(wda),
        GetTabBar(wda),
    ]
