"""WDA 工具共享基类 — 提供公共辅助函数和 WDA 客户端注入。"""

from __future__ import annotations

from typing import Any, Dict, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode
from wda_client import WDAClient


class WDABaseTool(Tool):
    """所有 WDA Action 工具的基类。

    统一持有 wda 客户端引用，并提供：
    - _ok() / _fail(): 快捷构建 ToolResponse
    - _safe_get_attr(): 安全属性获取
    - _smart_truncate_xml(): XML 智能截断
    - _find_scrollable_containers(): 查找可滚动容器
    """

    def __init__(self, wda: WDAClient, name: str, description: str):
        super().__init__(name=name, description=description)
        self.wda = wda

    # ---------- 快捷响应 ----------

    def _ok(self, text: str, data: dict | None = None) -> ToolResponse:
        return ToolResponse.success(text=text, data=data or {})

    def _fail(self, message: str) -> ToolResponse:
        return ToolResponse.error(code=ToolErrorCode.EXECUTION_ERROR, message=message)

    # ---------- 辅助函数 ----------

    def _safe_get_attr(self, element_id: str, attr_name: str, default: str = "N/A") -> str:
        """安全获取元素属性，失败返回默认值。"""
        try:
            val = self.wda.get_element_attribute(element_id, attr_name)
            return str(val) if val is not None else default
        except Exception:
            return default

    @staticmethod
    def _smart_truncate_xml(source: str, max_len: int = 25000) -> str:
        """智能截断 XML：在最后一个完整闭合标签处切断。"""
        if len(source) <= max_len:
            return source
        truncated = source[:max_len]
        cut = truncated.rfind("</")
        if cut > max_len * 0.8:
            return (
                truncated[:cut]
                + f"\n... [XML 已截断，原长度={len(source)}，建议用 inspect_element 查看特定元素]"
            )
        return truncated + f"\n... [XML 不完整截断，原长度={len(source)}，建议用 inspect_element]"

    def _find_scrollable_containers(self) -> list[str]:
        """查找页面中的可滚动容器。"""
        containers: list[str] = []
        for cls_name in ("XCUIElementTypeTable", "XCUIElementTypeCollectionView", "XCUIElementTypeScrollView"):
            try:
                containers.extend(self.wda.find_elements("class name", cls_name))
            except Exception:
                pass
        return containers

    def _is_visible(self, element_id: str) -> bool:
        """检查元素是否可见（异常时返回 True，降级处理）。"""
        try:
            return bool(self.wda.is_element_displayed(element_id))
        except Exception:
            return True  # 降级：假定可见

    def _find_by_name(self, name: str) -> str | None:
        """通过 name 查找元素，返回 element_id 或 None。"""
        return self.wda.find_element("name", name)
