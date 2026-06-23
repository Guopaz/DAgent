"""验证规则 — 定义各种验证规则。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from agent.models import ElementType, Observation, ValidationResult

if TYPE_CHECKING:
    pass


class ValidationRule:
    """验证规则基类。"""

    def check(self, before: Observation, after: Observation, action_type: str) -> ValidationResult:
        raise NotImplementedError


class PageChangedRule(ValidationRule):
    """检测页面是否发生变化。"""

    def check(self, before: Observation, after: Observation, action_type: str) -> ValidationResult:
        if before.page_name != after.page_name:
            return ValidationResult(
                passed=True,
                confidence=0.9,
                reason="页面名称已变化",
            )
        
        # 比较元素数量变化
        before_count = len(before.elements)
        after_count = len(after.elements)
        
        if before_count != after_count:
            diff = abs(after_count - before_count)
            return ValidationResult(
                passed=True,
                confidence=0.7,
                reason=f"元素数量变化: {before_count} → {after_count} (差异: {diff})",
            )
        
        return ValidationResult(
            passed=False,
            confidence=0.3,
            reason="页面未发生明显变化",
        )


class ElementAppearedRule(ValidationRule):
    """检测指定元素是否出现。"""

    def __init__(self, target_text: str):
        self.target_text = target_text

    def check(self, before: Observation, after: Observation, action_type: str) -> ValidationResult:
        before_texts = {e.text for e in before.elements if e.text}
        after_texts = {e.text for e in after.elements if e.text}
        
        if self.target_text in after_texts and self.target_text not in before_texts:
            return ValidationResult(
                passed=True,
                confidence=0.95,
                reason=f"目标元素 '{self.target_text}' 已出现",
            )
        
        if self.target_text in after_texts:
            return ValidationResult(
                passed=True,
                confidence=0.6,
                reason=f"目标元素 '{self.target_text}' 存在",
            )
        
        return ValidationResult(
            passed=False,
            confidence=0.4,
            reason=f"目标元素 '{self.target_text}' 未找到",
        )


class ElementDisappearedRule(ValidationRule):
    """检测指定元素是否消失。"""

    def __init__(self, target_text: str):
        self.target_text = target_text

    def check(self, before: Observation, after: Observation, action_type: str) -> ValidationResult:
        before_texts = {e.text for e in before.elements if e.text}
        after_texts = {e.text for e in after.elements if e.text}
        
        if self.target_text in before_texts and self.target_text not in after_texts:
            return ValidationResult(
                passed=True,
                confidence=0.9,
                reason=f"元素 '{self.target_text}' 已消失",
            )
        
        if self.target_text not in after_texts:
            return ValidationResult(
                passed=True,
                confidence=0.7,
                reason=f"元素 '{self.target_text}' 不存在",
            )
        
        return ValidationResult(
            passed=False,
            confidence=0.4,
            reason=f"元素 '{self.target_text}' 仍然存在",
        )


class NoAlertRule(ValidationRule):
    """检测没有弹窗。"""

    def check(self, before: Observation, after: Observation, action_type: str) -> ValidationResult:
        has_alert = any(e.type == ElementType.ALERT for e in after.elements)
        
        if not has_alert:
            return ValidationResult(
                passed=True,
                confidence=0.9,
                reason="无弹窗",
            )
        
        return ValidationResult(
            passed=False,
            confidence=0.8,
            reason="检测到弹窗",
        )
