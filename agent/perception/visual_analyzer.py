"""视觉分析器 — 当 UI 树不可用时，基于截图进行 LLM 辅助分析。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    pass


class VisualAnalyzer:
    """视觉分析器（降级方案，当 UI 树解析失败时使用）。"""

    def analyze(self, screenshot_base64: str, context: str = "") -> Dict[str, Any]:
        """分析截图，返回页面信息。
        
        注意：此功能需要 LLM 视觉能力支持，当前为占位实现。
        """
        return {
            "page_name": "视觉分析（未实现）",
            "elements": [],
            "description": "需要接入 LLM 视觉模型",
        }
