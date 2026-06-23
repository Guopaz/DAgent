"""交互工具 — 最核心的操作工具集：点击、输入、滚动、滑动、长按。"""

from __future__ import annotations

from typing import List

from hello_agents.tools import ToolParameter, ToolResponse

from tools._base import WDABaseTool


class TapElement(WDABaseTool):
    """通过 name、xpath 或 element_id 点击元素（最常用操作）。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="tap_element",
            description=(
                "点击元素。支持三种定位方式（三选一）：\n"
                "- name：通过元素的 label/name 定位（最常用）\n"
                "- xpath：通过 XPath 表达式定位（复杂场景）\n"
                "- element_id：直接使用元素 ID（从 find_element 等工具获取）\n"
                "点击前自动检查元素是否可见，点击后等待 1 秒等待 UI 过渡完成。\n"
                "使用场景：点击按钮、开关、菜单项等任何可交互元素\n"
                "示例：tap_element(name='设置') → 通过名称点击\n"
                "示例：tap_element(xpath='//XCUIElementTypeButton[@name=\"确认\"]') → 通过 XPath 点击\n"
                "示例：tap_element(element_id='12345') → 通过元素 ID 点击\n"
                "注意：如果元素不可见（在屏幕外），请使用 scroll_to_find_and_tap"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="元素的 label 或 name（三选一）",
                required=False,
            ),
            ToolParameter(
                name="xpath",
                type="string",
                description="XPath 定位表达式（三选一）",
                required=False,
            ),
            ToolParameter(
                name="element_id",
                type="string",
                description="元素 ID，从 find_element 等工具获取（三选一）",
                required=False,
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        name = params.get("name")
        xpath = params.get("xpath")
        element_id = params.get("element_id")

        # 参数校验：必须且只能提供一种定位方式
        provided = [p for p in (name, xpath, element_id) if p]
        if len(provided) == 0:
            return self._fail("请提供 name、xpath 或 element_id 之一来定位元素")
        if len(provided) > 1:
            return self._fail("请只提供 name、xpath、element_id 之一，不要同时提供多个")

        # 定位元素
        locator_desc = ""
        if name:
            element_id = self._find_by_name(name)
            locator_desc = f"name='{name}'"
            if not element_id:
                return self._fail(f"未找到元素：{locator_desc}，请先查看屏幕摘要确认元素名称")
        elif xpath:
            element_id = self.wda.find_element("xpath", xpath)
            locator_desc = f"xpath='{xpath}'"
            if not element_id:
                return self._fail(f"未找到匹配 XPath 的元素：{xpath}")
        else:
            locator_desc = f"element_id='{element_id}'"

        # 检查可见性
        if not self._is_visible(element_id):
            return self._fail(
                f"元素 {locator_desc} 在 DOM 中存在但当前不可见（可能在屏幕外或被遮挡），"
                "建议使用 scroll_to_find_and_tap 或先 clear_interrupt"
            )

        # 点击
        try:
            self.wda.click_element(element_id)
            self.wda.wait(1.0)
            return self._ok(f"✅ 已点击：{locator_desc}")
        except Exception as exc:
            return self._fail(f"点击失败：{locator_desc}（{exc}），建议查看屏幕摘要确认页面状态后重试")


class InputText(WDABaseTool):
    """在输入框中输入文本。"""

    # 输入框元素类型
    _INPUT_TYPES = (
        "XCUIElementTypeTextField",
        "XCUIElementTypeSecureTextField",
        "XCUIElementTypeTextView",
        "XCUIElementTypeSearchField",
    )

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="input_text",
            description=(
                "在输入框中输入文本。\n"
                "- name 可选：提供时按名称精确定位输入框；不提供时自动查找页面上的输入框（取最后一个）\n"
                "- 定位输入框后先点击聚焦（确保 keyboard 弹出且输入目标正确）\n"
                "- 点击后等待 0.3 秒，再清空已有内容，再输入新文本\n"
                "- 输入完成后自动关闭键盘\n"
                "使用场景：在搜索框、登录表单、设置项中输入文字\n"
                "示例：input_text(name='搜索', text='WiFi 密码') → 在搜索框中输入\n"
                "示例：input_text(text='hello') → 自动找到输入框并输入\n"
                "示例：input_text(name='Apple ID', text='user@example.com')"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="name",
                type="string",
                description="输入框的 label 或 name（可选，不提供时自动查找输入框）",
                required=False,
            ),
            ToolParameter(
                name="text",
                type="string",
                description="要输入的文本内容",
                required=True,
            ),
        ]

    def _find_input_fields(self) -> list[tuple[str, str]]:
        """查找页面上所有输入框，返回 [(element_id, name), ...] 列表。"""
        results: list[tuple[str, str]] = []
        for cls_name in self._INPUT_TYPES:
            try:
                element_ids = self.wda.find_elements("class name", cls_name)
            except Exception:
                continue
            for eid in element_ids:
                try:
                    label = self.wda.get_element_attribute(eid, "label") or ""
                except Exception:
                    label = ""
                try:
                    ename = self.wda.get_element_name(eid) or ""
                except Exception:
                    ename = ""
                display = label.strip() or ename.strip() or cls_name
                results.append((eid, display))
        return results

    def _locate_input(self, name: str | None) -> tuple[str | None, str]:
        """
        定位输入框。

        Returns:
            (element_id, description) — element_id 为 None 表示未找到
        """
        if name:
            # 优先按 name 精确查找
            element_id = self._find_by_name(name)
            if element_id:
                return element_id, f"name='{name}'"

            # name 未直接命中，查找所有输入框后倒序模糊匹配
            fields = self._find_input_fields()
            for eid, display in reversed(fields):
                if name.lower() in display.lower():
                    return eid, f"name='{name}' (模糊匹配到 '{display}')"

            return None, f"name='{name}'"

        # 未提供 name：查找所有输入框，取最后一个（通常是主输入框）
        fields = self._find_input_fields()
        if not fields:
            return None, "（页面上未找到任何输入框）"

        eid, display = fields[-1]
        return eid, f"自动选择输入框 '{display}'（共找到 {len(fields)} 个，取最后一个）"

    def run(self, params: dict) -> ToolResponse:
        name = params.get("name")
        text = params["text"]

        element_id, locator_desc = self._locate_input(name)
        if not element_id:
            return self._fail(f"未找到输入框：{locator_desc}，请查看屏幕摘要确认")

        # 步骤 1: 点击聚焦
        try:
            self.wda.click_element(element_id)
            self.wda.wait(0.3)
        except Exception as exc:
            return self._fail(f"点击输入框失败：{locator_desc}（{exc}）")

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
            return self._fail(f"输入文本失败：{locator_desc}（{exc}）")

        # 步骤 4: 关闭键盘
        try:
            self.wda.dismiss_keyboard()
        except Exception:
            pass

        return self._ok(f"✅ 已在 {locator_desc} 输入：{text}")


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


# 模块级共享缓存，供 GetTabBar 和 SwitchTabBar 共用
_tab_bar_cache = None


class _TabBarBase(WDABaseTool):
    """TabBar 工具的共享基类，封装辅助方法和缓存逻辑。"""

    def _find_tabbar(self) -> str | None:
        bars = self.wda.find_elements("class name", "XCUIElementTypeTabBar")
        return bars[0] if bars else None

    def _get_tab_items(self, tabbar_id: str) -> list[tuple[str, str]]:
        """遍历 TabBar 所有子元素，找出 label 不为空的元素并去重。"""
        try:
            all_children = self.wda.find_elements_from_element(tabbar_id, "xpath", ".//*")
        except Exception:
            return []

        seen_labels: set[str] = set()
        items: list[tuple[str, str]] = []

        for child_id in all_children:
            raw_label = self._safe_get_attr(child_id, "label", "").strip()
            if not raw_label:
                continue

            text = raw_label.split(",")[0].strip()
            if not text or text.isdigit():
                continue

            if text in seen_labels:
                continue
            seen_labels.add(text)
            items.append((child_id, text))

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
        global _tab_bar_cache
        if _tab_bar_cache is not None:
            return
        tabbar_id = self._find_tabbar()
        if not tabbar_id:
            _tab_bar_cache = False
            return
        items = self._get_tab_items(tabbar_id)
        if not items:
            _tab_bar_cache = False
            return
        tabs, sel_idx, sel_name = self._build_tab_info(items)
        _tab_bar_cache = {"element_ids": [eid for eid, _ in items],
                          "tabs": tabs,
                          "selected_index": sel_idx,
                          "selected_name": sel_name}


class GetTabBar(_TabBarBase):
    """获取底部 TabBar 的所有标签信息（只读）。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="get_tab_bar",
            description=(
                "获取底部 TabBar 的所有标签信息，返回结构化 Tab 列表（索引、名称、当前选中）。"
                "这是一个只读操作，不会切换 Tab。"
                "使用场景：先调用此工具了解 Tab 结构，再用 switch_tab_bar 切换。"
                "示例：get_tab_bar() → 列出所有 Tab"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        self._discover()
        if _tab_bar_cache is None or _tab_bar_cache is False:
            return self._ok(str({"found": False, "tab_count": 0, "selected_index": -1,
                "selected_name": "", "tabs": [], "reason": "当前页面未检测到 TabBar 或无法提取标签"}),
                {"found": False, "tab_count": 0, "selected_index": -1, "selected_name": "", "tabs": [],
                 "reason": "当前页面未检测到 TabBar 或无法提取标签"})

        c = _tab_bar_cache
        data = {"found": True, "tab_count": len(c["tabs"]),
                "selected_index": c["selected_index"], "selected_name": c["selected_name"],
                "tabs": c["tabs"]}
        return self._ok(str(data), data)


class SwitchTabBar(_TabBarBase):
    """切换到底部 TabBar 的指定标签（写操作）。"""

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="switch_tab_bar",
            description=(
                "切换到底部 TabBar 的指定标签。按 index（索引）或 tab_name（名称）切换。"
                "通常先调用 get_tab_bar() 获取 Tab 列表，再用此工具切换。"
                "示例：switch_tab_bar(index=3) → 切换到第 4 个 Tab"
                "示例：switch_tab_bar(tab_name='我的') → 按名称切换"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(name="index", type="integer",
                description="按索引切换（0-based）", required=False),
            ToolParameter(name="tab_name", type="string",
                description="按名称模糊匹配切换（不区分大小写）", required=False),
        ]

    def run(self, params: dict) -> ToolResponse:
        global _tab_bar_cache
        index = params.get("index")
        tab_name = params.get("tab_name")

        if index is not None and tab_name is not None:
            return self._fail("请只提供 index 或 tab_name 之一")
        if index is None and tab_name is None:
            return self._fail("请提供 index 或 tab_name")

        self._discover()
        if _tab_bar_cache is None or _tab_bar_cache is False:
            return self._fail("当前页面未检测到 TabBar 或无法提取标签")

        c = _tab_bar_cache
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
            _tab_bar_cache = None
            return self._ok(f"\u2705 已切换到 Tab [{target_idx}] {c['tabs'][target_idx]['screen_name']}")
        except Exception as exc:
            return self._fail(f"切换 Tab [{target_idx}] 失败: {exc}")


class TapKeyboardReturn(WDABaseTool):
    """快速点击键盘上的 Return/Done/Search/Send 键。"""

    # Return 键可能的名称（中英文）
    _RETURN_KEY_NAMES = {
        "return", "Return", "返回",
        "search", "Search", "搜索",
        "send", "Send", "发送",
        "done", "Done", "完成",
        "go", "Go", "前往",
        "join", "Join", "加入",
        "next", "Next", "下一个",
        "continue", "Continue", "继续",
        "submit", "Submit", "提交",
    }

    def __init__(self, wda):
        super().__init__(
            wda=wda,
            name="tap_keyboard_return",
            description=(
                "快速点击键盘上的确认键（Return/Done/Search/Send 等）。\n"
                "- 自动检测键盘是否弹出（通过 XCUIElementTypeKeyboard）\n"
                "- 自动识别确认键的类型（发送/搜索/完成/前往/提交等）\n"
                "- 点击后等待 0.5 秒\n"
                "使用场景：输入文本后需要按确认键提交（发送消息、搜索、提交表单等）\n"
                "示例：tap_keyboard_return() → 点击键盘确认键\n"
                "注意：input_text 已自动关闭键盘，仅在需要触发确认动作时使用"
            ),
        )

    def get_parameters(self) -> List[ToolParameter]:
        return []

    def run(self, params: dict) -> ToolResponse:
        # 步骤 1: 检查键盘是否弹出
        try:
            keyboards = self.wda.find_elements("class name", "XCUIElementTypeKeyboard")
        except Exception:
            keyboards = []

        if not keyboards:
            return self._fail("未检测到键盘，请先点击输入框或使用 input_text 输入文本")

        keyboard_id = keyboards[0]

        # 步骤 2: 在键盘中查找所有按钮
        try:
            buttons = self.wda.find_elements_from_element(
                keyboard_id, "class name", "XCUIElementTypeButton"
            )
        except Exception:
            buttons = []

        if not buttons:
            return self._fail("键盘中未找到任何按钮")

        # 步骤 3: 倒序遍历按钮，匹配确认键名称
        matched_id = None
        matched_name = ""
        for btn_id in reversed(buttons):
            try:
                label = (self.wda.get_element_attribute(btn_id, "label") or "").strip()
            except Exception:
                label = ""
            try:
                name = (self.wda.get_element_name(btn_id) or "").strip()
            except Exception:
                name = ""

            display = label or name
            if display in self._RETURN_KEY_NAMES:
                matched_id = btn_id
                matched_name = display
                break

        if not matched_id:
            # 回退：取最后一个按钮（通常是确认键）
            matched_id = buttons[-1]
            try:
                matched_name = (
                    self.wda.get_element_attribute(matched_id, "label") or ""
                ).strip() or "未知"
            except Exception:
                matched_name = "未知"

        # 步骤 4: 点击确认键
        try:
            self.wda.click_element(matched_id)
            self.wda.wait(0.5)
            return self._ok(f"✅ 已点击键盘确认键：'{matched_name}'")
        except Exception as exc:
            return self._fail(f"点击键盘确认键失败：{exc}")


def create_interaction_tools(wda) -> list[WDABaseTool]:
    return [
        TapElement(wda),
        InputText(wda),
        ScrollToFindAndTap(wda),
        SwipeDirection(wda),
        LongPressByName(wda),
        TapByCoordinate(wda),
        GetTabBar(wda),
        SwitchTabBar(wda),
        TapKeyboardReturn(wda),
    ]
