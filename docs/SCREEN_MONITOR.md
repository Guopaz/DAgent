# 屏幕监听器与上下文管理技术方案

## 问题背景

当前 Agent 的 ReAct 循环中，屏幕内容管理存在严重的效率问题：

```
Step 1: observe_screen → 返回 20000 字符 XML → 存入 messages
Step 2: tap_by_name    → 返回 "已点击"       → 存入 messages
Step 3: observe_screen → 返回 18000 字符 XML → 存入 messages  ← Step 1 的旧内容仍在
Step 4: tap_by_name    → 返回 "已点击"       → 存入 messages
Step 5: observe_screen → 返回 22000 字符 XML → 存入 messages  ← Step 1、3 的旧内容仍在
...
```

**核心问题**：
1. **旧屏幕内容不淘汰**：每次 observe_screen 的 XML（15000-30000 字符）作为 `role: tool` 消息永久留在 `messages` 列表中，随着步骤增加，历史消息中堆积大量过时的屏幕快照
2. **重复感知浪费步数**：Agent 每次操作后必须主动调用 observe_screen，浪费一个完整的 LLM 推理轮次
3. **Token 膨胀**：10 步任务中，屏幕 XML 可能占据 200K+ tokens，远超 LLM 上下文窗口
4. **信息噪声**：LLM 需要从大量旧屏幕状态中识别当前状态，降低推理质量

## 设计目标

1. **自动感知**：每个操作工具执行后自动刷新屏幕状态，无需 Agent 主动调用
2. **单帧缓存**：对话上下文中只保留最新一帧屏幕状态，旧帧自动淘汰
3. **步数节省**：消除 "操作 → 观察" 的固定 2 步模式，合并为 1 步
4. **Token 可控**：屏幕内容占用 tokens 保持恒定，不随步骤增长

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│  iOSAgent (extends ReActAgent)                          │
│                                                         │
│  ┌─────────────────┐    ┌────────────────────────────┐  │
│  │ ScreenMonitor    │    │ MessageContextManager      │  │
│  │                  │    │                            │  │
│  │ • latest_xml     │    │ • 管理 messages 列表       │  │
│  │ • refresh()      │    │ • 淘汰旧屏幕帧             │  │
│  │ • get_summary()  │    │ • 注入最新屏幕状态         │  │
│  │ • detect_changes │    │ • Token 预算控制           │  │
│  │ • mark_stale()   │    │                            │  │
│  └────────┬─────────┘    └──────────────┬─────────────┘  │
│           │                             │                │
│  ┌────────▼─────────────────────────────▼─────────────┐  │
│  │ ReActAgent Hook 机制（推荐）                        │  │
│  │                                                     │  │
│  │ before_llm_call(messages):                          │  │
│  │   → context_mgr.inject_screen(monitor, messages)   │  │
│  │                                                     │  │
│  │ after_tool_execution(tool_name, args, result):      │  │
│  │   → if is_action_tool: monitor.refresh()           │  │
│  │   → context_mgr.retire_old_screens(messages)       │  │
│  └─────────────────────────────────────────────────────┘  │
│                         │                                 │
│  ┌──────────────────────▼──────────────────────────────┐  │
│  │ WDAClient (保持不变)                                 │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**架构说明**：
- 采用 **Hook 机制**而非重写 `_run_impl`，降低与框架的耦合度
- `ReActAgent` 提供 `before_llm_call` 和 `after_tool_execution` 钩子
- `iOSAgent` 只需实现这两个钩子方法，无需复制整个循环逻辑
- 便于框架升级维护，只需关注屏幕管理逻辑本身

## 核心组件设计

### 1. ScreenMonitor — 屏幕状态监听器

```python
"""屏幕监听器 — 维护当前屏幕状态的单一事实来源"""

class ScreenMonitor:
    """
    屏幕状态监听器

    职责：
    - 维护最新屏幕快照（XML + 可选截图）
    - 提供屏幕摘要（精简格式，减少 token）
    - 变化检测（对比前后帧差异）
    - 自动刷新（操作后重新获取屏幕）

    线程安全：单线程 Agent 场景下无需加锁
    """

    def __init__(self, wda_client, xml_max_length: int = 20000, post_action_delay: float = 0.5):
        """
        Args:
            wda_client: WDAClient 实例
            xml_max_length: XML 最大保留长度，超出则截断
            post_action_delay: 动作工具执行后的等待时间（秒），等待 UI 过渡完成
        """
        self.wda = wda_client
        self.xml_max_length = xml_max_length
        self.post_action_delay = post_action_delay

        # 当前帧
        self._current_xml: str = ""
        self._current_summary: str = ""
        self._snapshot_time: float = 0
        self._snapshot_count: int = 0
        self._is_stale: bool = False  # 标记缓存是否过期（刷新失败时）

        # 上一帧（用于变化检测）
        self._previous_xml: str = ""

    def reset(self):
        """
        重置屏幕监听器状态
        
        在每次新任务开始前调用，清空所有缓存。
        用于多轮对话场景，确保任务间状态隔离。
        """
        self._current_xml = ""
        self._current_summary = ""
        self._snapshot_time = 0
        self._snapshot_count = 0
        self._previous_xml = ""
        self._is_stale = False

    def mark_stale(self):
        """
        标记屏幕状态为过期
        
        当自动刷新失败时调用，提示 Agent 需要主动调用 observe_screen。
        """
        self._is_stale = True

    def is_valid(self) -> bool:
        """
        检查缓存是否有效
        
        Returns:
            True 表示缓存有效，False 表示需要刷新
        """
        return not self._is_stale and self._current_xml != ""

    def refresh(self) -> str:
        """
        主动刷新屏幕状态

        调用 WDA get_source 获取最新 XML，更新缓存。
        同时将旧帧保存到 _previous_xml 用于 diff。
        
        刷新前会等待 UI 过渡完成（post_action_delay），
        并检测加载状态（如 ActivityIndicator），必要时等待加载完成。

        Returns:
            最新屏幕 XML（截断后）
        """
        # 等待 UI 过渡动画完成
        if self.post_action_delay > 0:
            time.sleep(self.post_action_delay)
        
        # 检测并等待加载状态（最多等待 3 秒）
        self._wait_for_loading_complete(timeout=3.0)

        self._previous_xml = self._current_xml

        raw_xml = self.wda.get_source() or ""
        self._current_xml = self._truncate(raw_xml)
        self._current_summary = self._build_summary(raw_xml)
        self._snapshot_time = time.time()
        self._snapshot_count += 1
        self._is_stale = False  # 刷新成功，标记为有效

        return self._current_xml
    
    def _wait_for_loading_complete(self, timeout: float = 3.0):
        """
        等待加载状态完成
        
        检测 XML 中是否存在加载指示器（ActivityIndicator、ProgressIndicator），
        如果存在则等待直到消失或超时。
        
        Args:
            timeout: 最大等待时间（秒）
        """
        import re
        
        start_time = time.time()
        loading_patterns = [
            r'type="XCUIElementTypeActivityIndicator"',
            r'type="XCUIElementTypeProgressIndicator"',
        ]
        
        while time.time() - start_time < timeout:
            try:
                xml = self.wda.get_source() or ""
                has_loading = any(re.search(pattern, xml) for pattern in loading_patterns)
                if not has_loading:
                    break
                time.sleep(0.3)  # 每 300ms 检查一次
            except Exception:
                break  # 查询失败时继续执行

    def get_current_xml(self) -> str:
        """获取缓存的最新 XML（不触发刷新）"""
        return self._current_xml

    def get_summary(self) -> str:
        """
        获取屏幕摘要（精简格式）

        从 XML 中提取关键元素，生成精简描述。
        比完整 XML 减少 70-80% 的 token 消耗。

        摘要格式示例：
        ```
        📱 当前页面：设置 > 无线局域网
        可见元素：
        - [Button] "返回" (enabled)
        - [Switch] "无线局域网" value=1
        - [Cell] "MyNetwork" ✓
        - [Cell] "OtherNetwork"
        - [Button] "其他..." (enabled)
        TabBar: 无
        ```
        """
        return self._current_summary

    def get_screen_state(self) -> dict:
        """
        获取完整屏幕状态（供消息注入使用）

        Returns:
            包含 XML、摘要、时间戳、变化标记的字典
        """
        return {
            "xml": self._current_xml,
            "summary": self._current_summary,
            "snapshot_time": self._snapshot_time,
            "snapshot_count": self._snapshot_count,
            "has_changed": self._current_xml != self._previous_xml,
        }

    def detect_changes(self) -> str:
        """
        检测屏幕变化（前后帧 diff）

        包含两级检测：
        1. 页面级变化：比较 NavigationBar 标题，判断是否发生页面跳转
        2. 元素级变化：比较元素 name 集合的增减

        Returns:
            变化描述文本，无变化则返回空字符串

        用途：在操作后向 Agent 报告"什么变了"
        """
        if not self._previous_xml:
            return "（首次获取屏幕，无对比基线）"

        if self._current_xml == self._previous_xml:
            return "（屏幕未发生变化）"

        # 页面级变化检测：比较 NavigationBar 标题
        old_nav = self._extract_nav_title(self._previous_xml)
        new_nav = self._extract_nav_title(self._current_xml)
        if old_nav and new_nav and old_nav != new_nav:
            return f"📄 页面跳转: \"{old_nav}\" → \"{new_nav}\""

        # 元素级变化：比较关键元素的增减
        old_elements = self._extract_element_names(self._previous_xml)
        new_elements = self._extract_element_names(self._current_xml)

        added = new_elements - old_elements
        removed = old_elements - new_elements

        parts = []
        if added:
            parts.append(f"新增元素: {', '.join(list(added)[:5])}")
        if removed:
            parts.append(f"消失元素: {', '.join(list(removed)[:5])}")

        return "；".join(parts) if parts else "（页面结构有变化）"

    def _extract_nav_title(self, xml: str) -> str:
        """从 XML 提取 NavigationBar 标题"""
        import re
        match = re.search(
            r'type="XCUIElementTypeNavigationBar"[^>]*name="([^"]*)"', xml
        )
        return match.group(1) if match else ""

    def _truncate(self, xml: str) -> str:
        """截断 XML 到最大长度"""
        if len(xml) <= self.xml_max_length:
            return xml
        return xml[:self.xml_max_length] + f"\n... [XML 截断，总长度={len(xml)}]"

    def _build_summary(self, xml: str) -> str:
        """
        从 XML 构建精简摘要

        解析 WDA 的 XML 元素树，提取：
        - 页面标题/导航栏
        - 可见的交互元素（按钮、开关、输入框、单元格、链接等）
        - TabBar 结构
        - 弹窗状态
        - 列表聚合信息（如"通讯录列表，共 50 个联系人"）

        使用 xml.etree.ElementTree 做结构化解析（替代正则），
        更可靠地处理不同 iOS 版本的 XML 格式差异。
        """
        import xml.etree.ElementTree as ET

        if not xml:
            return "（无法获取屏幕信息）"

        lines = ["📱 当前屏幕："]

        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            # XML 解析失败时降级为正则
            return self._build_summary_fallback(xml)

        # 提取导航栏标题
        nav_bars = root.findall('.//*[@type="XCUIElementTypeNavigationBar"]')
        for nav in nav_bars:
            name = nav.get("name", "")
            if name:
                lines.append(f"导航栏: {name}")

        # 提取关键交互元素
        interactive_types = {
            "XCUIElementTypeButton": "🔘",
            "XCUIElementTypeSwitch": "🔀",
            "XCUIElementTypeTextField": "📝",
            "XCUIElementTypeSecureTextField": "🔒",
            "XCUIElementTypeSlider": "🎚️",
            "XCUIElementTypeTab": "📑",
            "XCUIElementTypeCell": "📋",
            "XCUIElementTypeLink": "🔗",
            "XCUIElementTypeImage": "🖼️",
            "XCUIElementTypePickerWheel": "🎡",
            "XCUIElementTypeSearchField": "🔍",
        }

        elements_found = []
        for elem in root.iter():
            elem_type = elem.get("type", "")
            name = elem.get("name", "")
            if not name or len(name) >= 50:
                continue

            icon = interactive_types.get(elem_type)
            if icon:
                short_type = elem_type.split("XCUIElementType")[-1]
                value = elem.get("value", "")
                value_str = f" value={value}" if value else ""
                elements_found.append(f"  {icon} [{short_type}] \"{name}\"{value_str}")

        # 提取静态文本（前 10 个）
        static_texts = []
        for elem in root.iter():
            if elem.get("type") == "XCUIElementTypeStaticText":
                name = elem.get("name", "")
                if name and len(name) < 50:
                    static_texts.append(f"  📄 \"{name}\"")
        elements_found.extend(static_texts[:10])

        if elements_found:
            lines.append("可见元素:")
            lines.extend(elements_found[:25])  # 最多显示 25 个元素

        # 检测 TabBar
        tabs = [elem.get("name") for elem in root.iter()
                if elem.get("type") == "XCUIElementTypeTab" and elem.get("name")]
        if tabs:
            lines.append(f"TabBar: {', '.join(tabs)}")

        # 检测弹窗
        alerts = [elem.get("name", "未命名弹窗") for elem in root.iter()
                  if elem.get("type") == "XCUIElementTypeAlert"]
        if alerts:
            lines.append(f"⚠️ 弹窗: {alerts[0]}")

        # 列表聚合：如果 Cell 数量超过阈值，显示聚合信息
        cells = [elem for elem in root.iter()
                 if elem.get("type") == "XCUIElementTypeCell"]
        if len(cells) > 10:
            visible_names = [c.get("name", "") for c in cells if c.get("name")][:5]
            lines.append(f"📋 列表: 共 {len(cells)} 项，当前可见: {', '.join(visible_names)}...")

        return "\n".join(lines)

    def _build_summary_fallback(self, xml: str) -> str:
        """XML 解析失败时的降级方案（使用正则）"""
        import re
        lines = ["📱 当前屏幕：（XML 解析降级）"]
        nav_match = re.findall(
            r'type="XCUIElementTypeNavigationBar"[^>]*name="([^"]*)"', xml
        )
        if nav_match:
            lines.append(f"导航栏: {' > '.join(nav_match)}")
        names = re.findall(r'name="([^"]{1,50})"', xml)
        if names:
            lines.append("可见元素:")
            for name in names[:15]:
                lines.append(f"  • \"{name}\"")
        return "\n".join(lines)

    def _extract_element_names(self, xml: str) -> set:
        """从 XML 提取所有元素 name 集合（用于 diff）"""
        import re
        return set(re.findall(r'name="([^"]+)"', xml))
```

### 2. MessageContextManager — 消息上下文管理器

```python
"""消息上下文管理器 — 控制对话中屏幕状态的注入和淘汰"""

SCREEN_MARKER = "<screen-state>"
SCREEN_MARKER_END = "</screen-state>"


class MessageContextManager:
    """
    消息上下文管理器

    职责：
    - 在每轮 LLM 调用前注入最新屏幕状态
    - 淘汰消息历史中的旧屏幕帧
    - 控制屏幕内容在上下文中的 token 预算
    - 管理自动观察消息的格式

    设计原则：
    - 屏幕状态作为 system 消息注入，不参与 tool_call 配对
    - 只保留最新一帧，旧帧替换为摘要引用
    - 屏幕内容 token 预算可配置
    """

    def __init__(
        self,
        screen_token_budget: int = 8000,
        use_summary: bool = True,
        inject_mode: str = "summary",
    ):
        """
        Args:
            screen_token_budget: 屏幕内容最大 token 预算
            use_summary: 是否使用精简摘要（True）或完整 XML（False）
            inject_mode: 注入模式
                - "summary": 只注入摘要（最省 token）
                - "xml": 注入完整 XML
                - "both": 摘要 + 截断 XML
        """
        self.screen_token_budget = screen_token_budget
        self.use_summary = use_summary
        self.inject_mode = inject_mode

    def inject_screen_state(
        self,
        messages: list,
        monitor: 'ScreenMonitor',
    ) -> None:
        """
        在 messages 中注入最新屏幕状态

        注入策略（解决 LLM API 消息序列兼容性问题）：
        - 动态修改第一条 system 消息的末尾，追加屏幕状态
        - 避免在 assistant/tool 消息之间插入 system 消息（会破坏 API 规范）
        - 旧屏幕状态自动替换，只保留最新一帧

        注入内容示例：
        ```
        <screen-state>
        📱 当前屏幕：
        导航栏: 设置 > 无线局域网
        可见元素:
          🔘 [Button] "返回"
          🔀 [Switch] "无线局域网"
          📑 Tab: "Wi-Fi", "蓝牙", "蜂窝"

        变化: 新增元素: "MyNetwork"；消失元素: "搜索中..."
        </screen-state>
        ```
        """
        # 先淘汰旧屏幕
        self.retire_old_screens(messages)

        # 构建注入内容
        state = monitor.get_screen_state()
        changes = monitor.detect_changes()

        if self.inject_mode == "summary":
            content = f"\n\n{SCREEN_MARKER}\n{state['summary']}\n"
            if changes:
                content += f"\n变化: {changes}\n"
            content += SCREEN_MARKER_END
        elif self.inject_mode == "xml":
            content = f"\n\n{SCREEN_MARKER}\n{state['xml']}\n{SCREEN_MARKER_END}"
        else:  # both
            content = f"\n\n{SCREEN_MARKER}\n{state['summary']}\n"
            if changes:
                content += f"\n变化: {changes}\n"
            content += f"\n<xml>\n{state['xml']}\n</xml>\n"
            content += SCREEN_MARKER_END

        # 找到第一条 system 消息，在其末尾追加屏幕状态
        for msg in messages:
            if msg.get("role") == "system":
                msg["content"] = msg.get("content", "") + content
                break
        else:
            # 如果没有 system 消息，在开头插入一条
            messages.insert(0, {
                "role": "system",
                "content": content.lstrip(),
            })

    def retire_old_screens(self, messages: list) -> None:
        """
        淘汰消息列表中的旧屏幕帧

        策略：
        - 扫描所有 messages，找到包含 SCREEN_MARKER 的 system 消息
        - 将 system 消息中的旧 <screen-state>...</screen-state> 块替换为简短引用
        - 只保留最新一帧的完整内容

        这确保 messages 中永远只有一帧完整屏幕状态。
        """
        import re

        for msg in messages:
            if msg.get("role") != "system":
                continue
            content = msg.get("content", "")
            if SCREEN_MARKER not in content:
                continue

            # 找到所有 <screen-state>...</screen-state> 块
            pattern = rf'{re.escape(SCREEN_MARKER)}.*?{re.escape(SCREEN_MARKER_END)}'
            matches = list(re.finditer(pattern, content, re.DOTALL))

            if len(matches) <= 1:
                continue

            # 保留最后一个，替换之前的
            for match in matches[:-1]:
                content = content[:match.start()] + "（旧屏幕状态已淘汰）" + content[match.end():]

            msg["content"] = content

    def prune_tool_results(self, messages: list, keep_recent: int = 3) -> None:
        """
        裁剪旧的工具执行结果

        对于 role=tool 的消息，只保留最近 keep_recent 条的完整内容，
        更早的替换为摘要引用。

        目的：防止工具结果（特别是 observe_screen 的 XML）无限膨胀。

        Args:
            messages: 消息列表（原地修改）
            keep_recent: 保留最近 N 条完整工具结果
        """
        tool_indices = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "tool":
                tool_indices.append(i)

        # 对超出 keep_recent 的旧工具结果进行裁剪
        to_prune = tool_indices[:-keep_recent] if len(tool_indices) > keep_recent else []

        for idx in to_prune:
            original = messages[idx]["content"]
            if len(original) > 200:
                messages[idx]["content"] = f"[工具结果已裁剪] {original[:100]}..."
```

### 3. 工具分类标记

```python
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
```

### 4. ReActAgent Hook 机制 — 框架层改造

```python
"""
在 ReActAgent 基类中增加 Hook 支持

设计原则：
- 最小侵入：只在 _run_impl 的关键节点插入 hook 调用
- 向后兼容：默认 hook 为空实现，不影响其他 Agent
- 职责单一：hook 只负责屏幕管理，不修改核心循环逻辑
"""

class ReActAgent(Agent):
    # ...existing code...

    def _run_impl(self, input_text: str, session_start_time, **kwargs) -> str:
        messages = self._build_messages(input_text)
        tool_schemas = self._build_tool_schemas()

        # ★ Hook: 循环开始前（子类可覆写，用于初始化屏幕监听等）
        self._on_loop_start(messages)

        current_step = 0
        total_tokens = 0

        while current_step < self.max_steps:
            current_step += 1
            self._current_step = current_step

            # ★ Hook: 每步 LLM 调用前（子类可覆写，用于注入屏幕状态）
            self._before_llm_call(messages)

            # 调用 LLM（原有逻辑不变）
            response = self.llm.invoke_with_tools(messages, tool_schemas, ...)
            # ...existing code...

            # 执行工具调用
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                arguments = json.loads(tool_call.function.arguments)
                # ...existing code...

                result = self._execute_tool_call(tool_name, arguments)
                messages.append({"role": "tool", ...})

                # ★ Hook: 工具执行后（子类可覆写，用于自动刷新屏幕）
                self._after_tool_execution(messages, tool_name, arguments, result)

            # ★ Hook: 每步结束后（子类可覆写，用于裁剪消息等）
            self._after_step(messages, current_step)

        return "任务未完成：已达到最大步数限制。"

    # ---- Hook 方法（默认空实现，子类按需覆写）----

    def _on_loop_start(self, messages: list):
        """循环开始前调用，用于初始化"""
        pass

    def _before_llm_call(self, messages: list):
        """每次 LLM 调用前调用"""
        pass

    def _after_tool_execution(self, messages: list, tool_name: str, arguments: dict, result: str):
        """工具执行后调用"""
        pass

    def _after_step(self, messages: list, step: int):
        """每步结束后调用"""
        pass
```

### 5. iOSReActAgent — 通过 Hook 集成屏幕管理

```python
"""带屏幕监听的 iOS ReAct Agent — 通过 Hook 机制集成，无需重写主循环"""

class iOSReActAgent(ReActAgent):
    """
    集成屏幕监听器的 ReAct Agent

    与原生 ReActAgent 的区别：
    1. 每步开始时自动注入最新屏幕状态到 messages
    2. 动作工具执行后自动刷新屏幕缓存
    3. 旧的屏幕帧自动淘汰，只保留最新一帧
    4. observe_screen 工具从缓存读取（零 WDA 调用）

    ReAct 循环变化：

    原生循环（每步 2 次 LLM 调用）：
    ```
    Step N:
      LLM → observe_screen → [XML 入 messages]
      LLM → tap_by_name → [结果入 messages]
    Step N+1:
      LLM → observe_screen → [又一份 XML 入 messages]  ← 旧的仍在
      LLM → tap_by_name
    ```

    优化循环（每步 1 次 LLM 调用）：
    ```
    Step N:
      [自动注入屏幕摘要]
      LLM → tap_by_name → [自动刷新屏幕] → [淘汰旧帧]
    Step N+1:
      [自动注入最新屏幕摘要]
      LLM → input_text_by_name → [自动刷新屏幕] → [淘汰旧帧]
    ```

    效果：步骤减半，token 恒定。
    """

    def __init__(self, wda_client, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 创建屏幕监听器和上下文管理器
        self.screen_monitor = ScreenMonitor(wda_client)
        self.context_manager = MessageContextManager(
            screen_token_budget=8000,
            use_summary=True,
            inject_mode="summary",
        )

    def run(self, task: str, **kwargs) -> str:
        """每次任务开始前重置屏幕状态"""
        self.screen_monitor.reset()
        return super().run(task, **kwargs)

    # ---- Hook 实现 ----

    def _on_loop_start(self, messages: list):
        """循环开始前：获取初始屏幕快照"""
        self.screen_monitor.refresh()

    def _before_llm_call(self, messages: list):
        """LLM 调用前：注入最新屏幕状态到 system 消息"""
        self.context_manager.inject_screen_state(messages, self.screen_monitor)

    def _after_tool_execution(self, messages, tool_name, arguments, result):
        """工具执行后：动作工具自动刷新屏幕"""
        if is_action_tool(tool_name, arguments):
            try:
                self.screen_monitor.refresh()
                print(f"📱 屏幕已刷新 (第{self.screen_monitor._snapshot_count}帧)")
            except Exception as e:
                # 降级：标记屏幕状态为过期，让 Agent 主动调用 observe_screen
                self.screen_monitor.mark_stale()
                print(f"⚠️ 屏幕自动刷新失败: {e}，下一步需主动观察")

    def _after_step(self, messages: list, step: int):
        """每步结束后：裁剪旧工具结果，防止消息膨胀"""
        self.context_manager.prune_tool_results(messages, keep_recent=3)
```

### 6. observe_screen 改造为缓存读取

```python
"""
改造后的 observe_screen：从缓存读取，零 WDA 调用

原来：每次调用都请求 WDA get_source，耗时 ~200ms
现在：直接从 ScreenMonitor 缓存读取，耗时 ~0ms

适配方式：通过构造函数注入 ScreenMonitor 实例，
保持与现有 WDABaseTool 框架的兼容性。
"""

class ObserveScreen(WDABaseTool):
    """获取当前屏幕状态（优先从缓存读取）"""

    def __init__(self, wda, monitor: ScreenMonitor = None):
        super().__init__(
            wda=wda,
            name="observe_screen",
            description=(
                "获取当前屏幕状态。\n"
                "- 屏幕状态在每个操作后自动刷新，此工具从缓存读取，零延迟\n"
                "- mode='summary'（默认）：返回精简摘要\n"
                "- mode='xml'：返回完整 XML 元素树\n"
                "- mode='screenshot'：返回截图 base64（需要实际 WDA 调用）\n"
                "注意：通常无需主动调用此工具，屏幕状态已自动注入到上下文中"
            ),
        )
        self.monitor = monitor  # 可选注入，None 时降级为直接调用 WDA

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="mode",
                type="string",
                description="获取模式：'summary'（默认）/ 'xml' / 'screenshot'",
                required=False,
                default="summary",
            ),
        ]

    def run(self, params: dict) -> ToolResponse:
        mode = params.get("mode", "summary")

        # 截图模式：始终需要实际 WDA 调用
        if mode == "screenshot":
            data = self.wda.get_screenshot()
            if not data:
                return self._fail("无法获取截图")
            if len(data) > 30000:
                return self._ok(f"[截图已获取, base64 长度={len(data)}, 已截断以节省上下文]")
            return self._ok(data)

        # 有缓存时从缓存读取
        if self.monitor and self.monitor.is_valid():
            state = self.monitor.get_screen_state()
            changes = self.monitor.detect_changes()

            if mode == "xml":
                xml = state["xml"]
                if len(xml) > 20000:
                    return self._ok(
                        xml[:20000] + f"\n... [XML 截断，总长度={len(xml)}，"
                        "建议用 inspect_element 查看特定元素]"
                    )
                return self._ok(xml)

            # 默认 summary 模式
            result = state["summary"]
            if changes:
                result += f"\n\n最近变化: {changes}"
            result += f"\n\n📊 快照 #{state['snapshot_count']}"
            return self._ok(result)

        # 降级：无缓存时直接调用 WDA
        source = self.wda.get_source()
        if not source:
            return self._fail("无法获取屏幕 XML")
        return self._ok(self._smart_truncate_xml(source))
```

## 消息流对比

### 优化前（当前实现）

```
messages = [
  {system: "你是 iPhone Agent..."},           # ~800 tokens
  {user: "打开WiFi设置"},                      # ~20 tokens
  ── Step 1 ──
  {assistant: tool_calls=[observe_screen]},    # ~50 tokens
  {tool: observe_screen → 25000 字符 XML},     # ~6000 tokens ★
  {assistant: tool_calls=[tap_by_name]},       # ~80 tokens
  {tool: tap_by_name → "已点击: 设置"},        # ~20 tokens
  ── Step 2 ──
  {assistant: tool_calls=[observe_screen]},    # ~50 tokens
  {tool: observe_screen → 22000 字符 XML},     # ~5500 tokens ★★ 旧的 6000 仍在！
  {assistant: tool_calls=[tap_by_name]},       # ~80 tokens
  {tool: tap_by_name → "已点击: WiFi"},        # ~20 tokens
  ── Step 3 ──
  {assistant: tool_calls=[observe_screen]},    # ~50 tokens
  {tool: observe_screen → 18000 字符 XML},     # ~4500 tokens ★★★ 前两份仍在！
  ...
]
Total at Step 3: ~800 + 2×(6000+5500+4500) + ... ≈ 38000+ tokens
```

### 优化后（屏幕监听器）

```
messages = [
  {system: "你是 iPhone Agent...\n\n<screen-state>摘要...</screen-state>"},  # ~1300 tokens ★
  {user: "打开WiFi设置"},                      # ~20 tokens
  ── Step 1 ──
  {assistant: tool_calls=[tap_by_name]},       # ~80 tokens
  {tool: tap_by_name → "已点击: 设置"},        # ~20 tokens
  ── Step 2 ──
  {system: "...（旧屏幕状态已淘汰）\n\n<screen-state>新摘要...</screen-state>"},  # ~1320 tokens ★★
  {assistant: tool_calls=[tap_by_name]},       # ~80 tokens
  {tool: tap_by_name → "已点击: WiFi"},        # ~20 tokens
  ── Step 3 ──
  {system: "...（旧屏幕状态已淘汰）\n\n<screen-state>新摘要...</screen-state>"},  # ~1320 tokens ★★★
  ...
]
Total at Step 3: ~1300 + 2×20 + 2×80 + ... ≈ 1700 tokens
```

**关键改进**：
- 屏幕状态**追加到第一条 system 消息末尾**，避免破坏消息序列
- 旧屏幕状态在 system 消息内部被替换，不产生新的 system 消息
- Token 消耗恒定，不随步骤增长

**Token 节省**：38000 → 1700，减少 **95%**

## 工具层变化

### observe_screen 的角色变化

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 触发方式 | Agent 主动调用 | 动作工具后自动刷新 |
| WDA 调用 | 每次 1 次 get_source | 自动刷新时 1 次 |
| 消息中的位置 | role=tool（累积） | role=system（只保留最新） |
| 返回内容 | 完整 XML | 精简摘要（可切换） |
| Token 占用 | ~6000/帧 | ~500/帧 |
| 对 Agent 的意义 | 需要主动感知 | 始终可见，无需主动调用 |

### 工具优先级调整

系统提示词中移除 "先 observe 再 action" 的强制要求，改为：

```
## 屏幕感知
- 屏幕状态在每个操作后自动刷新，你始终能看到最新页面
- 无需每次操作前主动调用 observe_screen
- 如果需要更详细的元素信息，使用 inspect_element
- 如果需要完整 XML（如写 XPath），使用 observe_screen(mode='xml')
```

## 文件结构

```
DAgent/
├── agent.py                     # iOSAgent（通过 Hook 集成 ScreenMonitor + ContextManager）
├── core/
│   ├── __init__.py
│   ├── screen_monitor.py        # ScreenMonitor 屏幕监听器
│   └── context_manager.py       # MessageContextManager 上下文管理器
├── hello_agents/
│   └── agents/
│       └── react_agent.py       # 增加 Hook 方法（_on_loop_start, _before_llm_call 等）
├── tools/
│   ├── __init__.py              # build_tool_registry（注入 ScreenMonitor 到 observe_screen）
│   ├── adapter.py               # WDAFunctionTool 适配器
│   ├── perception.py            # observe_screen 改为缓存读取（注入 monitor）
│   ├── interaction.py           # 保持不变
│   ├── app_lifecycle.py         # 保持不变
│   ├── device_info.py           # 保持不变
│   ├── error_handling.py        # 保持不变
│   └── tool_categories.py       # 工具分类标记（OBSERVATION_TOOLS / ACTION_TOOLS / CONDITIONAL_ACTION_TOOLS）
├── wda_client.py                # 保持不变
└── docs/
    └── SCREEN_MONITOR.md        # 本文档
```

## 实施步骤

### Phase 1：核心组件（2-3 小时）

1. 创建 `core/screen_monitor.py`，实现 ScreenMonitor
   - `refresh()`、`get_summary()`、`detect_changes()`、`reset()`、`mark_stale()`、`is_valid()`
   - `_wait_for_loading_complete()` 加载状态检测
   - 使用 `xml.etree.ElementTree` 做结构化解析（替代正则）
   - 摘要覆盖更多元素类型：Cell、Link、Image、PickerWheel 等
   - 验证：单元测试摘要生成质量、加载等待逻辑
2. 创建 `core/context_manager.py`，实现 MessageContextManager
   - `inject_screen_state()`：追加到第一条 system 消息末尾
   - `retire_old_screens()`：在 system 消息内部替换旧 `<screen-state>` 块
   - `prune_tool_results()`：裁剪旧工具结果
   - 验证：模拟消息列表，确认旧帧正确淘汰、消息序列符合 API 规范

### Phase 2：框架层 Hook 改造（1 小时）

1. 修改 `hello_agents/agents/react_agent.py`
   - 在 `_run_impl()` 中插入 4 个 Hook 调用点：
     - `_on_loop_start(messages)` — 循环开始前
     - `_before_llm_call(messages)` — 每次 LLM 调用前
     - `_after_tool_execution(messages, tool_name, arguments, result)` — 工具执行后
     - `_after_step(messages, step)` — 每步结束后
   - 默认实现为空方法，不影响其他 Agent
   - 验证：确保现有 Agent 行为不变

### Phase 3：Agent 集成（1-2 小时）

1. 修改 `agent.py` 中 iOSAgent
   - 覆写 4 个 Hook 方法，注入 ScreenMonitor 和 MessageContextManager
   - 覆写 `run()` 方法，在任务开始前调用 `screen_monitor.reset()`
   - 验证：运行一个简单任务，观察日志中自动刷新行为
2. 创建 `tools/tool_categories.py`
   - 定义 `OBSERVATION_TOOLS`、`ACTION_TOOLS`、`CONDITIONAL_ACTION_TOOLS`
   - 实现 `is_action_tool(tool_name, arguments)` 支持混合型工具判断

### Phase 4：工具层适配（1 小时）

1. 修改 `tools/perception.py` 中的 `ObserveScreen`
   - 构造函数接受可选的 `monitor: ScreenMonitor` 参数
   - 有缓存时从缓存读取，无缓存时降级为直接调用 WDA
   - 支持 `mode='summary'` / `'xml'` / `'screenshot'`
2. 修改 `tools/__init__.py` 中的 `build_tool_registry`
   - 接受 `monitor` 参数，传递给 `ObserveScreen`
3. 更新系统提示词
   - 移除 "先观察再操作" 的强制要求
   - 说明屏幕自动刷新机制
   - 说明 `observe_screen` 的新用途（仅在需要详细信息时使用）

### Phase 5：验证和优化（1-2 小时）

1. 对比测试：相同任务在优化前后的表现
   - 量化指标：
     - 步骤数（完成同一任务的 step 数）
     - LLM 调用次数（实际 invoke 次数）
     - 总 Token 消耗（input + output tokens）
     - WDA 调用次数（get_source 调用次数）
     - 任务成功率（10 次运行的成功比例）
     - 平均耗时（端到端完成时间）
     - 摘要信息丢失率（因摘要不全导致额外调用 inspect_element 的次数）
2. 调优：根据测试结果调整
   - 摘要格式（信息密度 vs token 消耗）
   - `post_action_delay` 时长（0.3s ~ 1.0s）
   - `inject_mode` 选择（summary / xml / both）
   - 加载等待超时时间

## 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 摘要丢失关键元素 | Agent 找不到元素 | 使用 `xml.etree.ElementTree` 结构化解析；覆盖 Cell、Link、Image、PickerWheel 等类型；保留 `mode='xml'` 降级路径 |
| Hook 改造影响其他 Agent | 现有 Agent 行为可能变化 | Hook 默认实现为空方法；增加单元测试验证现有 Agent 不受影响 |
| 自动刷新增加 WDA 调用 | 每步多 ~200ms + post_action_delay | 对比节省的 LLM 推理时间（1-3s），净收益为正；`post_action_delay` 可配置 |
| 自动刷新失败 | 屏幕状态过期，Agent 决策失误 | `mark_stale()` 降级机制；`observe_screen` 检测到 stale 时直接调用 WDA |
| UI 过渡动画未完成就刷新 | 捕获到中间状态（半弹出菜单等） | `_wait_for_loading_complete()` 检测 ActivityIndicator；可配置 `post_action_delay` |
| 多轮对话状态污染 | 新任务看到旧任务的屏幕状态 | `run()` 入口调用 `screen_monitor.reset()` 清空状态 |
| diff 检测不准确 | 变化描述误导 Agent | 增加页面级变化检测（NavigationBar 标题对比）；简单 diff 足够，不追求精确 |
| 混合型工具判断错误 | 该刷新时没刷新或不该刷新时刷新 | `CONDITIONAL_ACTION_TOOLS` 根据参数动态判断；宁可多刷新也不漏刷新 |

## 总结

| 维度 | 优化前 | 优化后 |
|------|--------|--------|
| 每步 LLM 调用 | 2 次（观察 + 操作） | 1 次（操作，屏幕自动注入） |
| 屏幕内容 token | ~6000/帧，累积增长 | ~500/帧，恒定不变 |
| 10 步任务总 token | ~80K+ | ~15K |
| Agent 需要主动感知 | 是（每步都要） | 否（自动刷新） |
| 旧屏幕内容处理 | 不处理（永久累积） | 自动淘汰（只保留最新） |
| 框架耦合度 | 重写 `_run_impl`（高耦合） | Hook 机制（低耦合） |
| 消息序列兼容性 | 插入 system 消息（可能报错） | 追加到已有 system 消息（兼容） |
| 工具分类 | 静态分类 | 支持混合型工具动态判断 |
| 刷新失败处理 | 无降级策略 | `mark_stale()` + 降级到 WDA 直调 |
| UI 过渡处理 | 无等待机制 | `post_action_delay` + 加载状态检测 |
| 多轮对话 | 状态可能污染 | `reset()` 确保任务间隔离 |
