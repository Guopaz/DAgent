"""屏幕监听器 — 维护当前屏幕状态的单一事实来源"""

import re
import time
import xml.etree.ElementTree as ET
from typing import Optional
from wda_client import WDAClient


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

    def __init__(self, wda_client: WDAClient, xml_max_length: int = 30000, post_action_delay: float = 0.5):
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
        return set(re.findall(r'name="([^"]+)"', xml))
