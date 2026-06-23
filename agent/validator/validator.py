"""验证器 — 独立验证执行结果。"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from agent.models import Observation, ValidationResult
from agent.validator.rules import (
    ElementAppearedRule,
    ElementDisappearedRule,
    NoAlertRule,
    PageChangedRule,
    ValidationRule,
)

if TYPE_CHECKING:
    pass


class Validator:
    """验证器 — 执行三级验证。"""

    def __init__(self):
        self.rules: List[ValidationRule] = []

    def validate(
        self,
        before: Observation,
        after: Observation,
        action_type: str,
        step_description: str = "",
    ) -> ValidationResult:
        """执行验证，返回综合结果。"""
        # 构建验证规则
        rules = self._build_rules(action_type, step_description)
        
        results = []
        for rule in rules:
            result = rule.check(before, after, action_type)
            results.append(result)

        # 综合评估
        if not results:
            return ValidationResult(
                passed=False,
                confidence=0.0,
                reason="无验证规则",
            )

        passed_count = sum(1 for r in results if r.passed)
        avg_confidence = sum(r.confidence for r in results) / len(results)
        
        # 多数规则通过即视为通过
        passed = passed_count > len(results) / 2
        
        reasons = [r.reason for r in results]
        
        return ValidationResult(
            passed=passed,
            confidence=avg_confidence,
            reason="; ".join(reasons),
            details={
                "total_rules": len(results),
                "passed_rules": passed_count,
                "individual_results": [
                    {"passed": r.passed, "confidence": r.confidence, "reason": r.reason}
                    for r in results
                ],
            },
        )

    def _build_rules(self, action_type: str, step_description: str) -> List[ValidationRule]:
        """根据动作类型构建验证规则。"""
        rules = [
            PageChangedRule(),
            NoAlertRule(),
        ]
        
        # 根据步骤描述添加特定规则
        if "点击" in step_description or "click" in step_description.lower():
            # 点击后期望页面变化
            pass
        
        if "输入" in step_description or "input" in step_description.lower():
            # 输入后期望看到输入的内容
            pass
        
        return rules

    def validate_step_completion(
        self,
        observation: Observation,
        step_description: str,
    ) -> ValidationResult:
        """验证步骤是否完成（使用 LLM）。"""
        # 简化实现：基于关键词匹配
        page_text = " ".join([e.text for e in observation.elements if e.text])
        
        # 提取步骤中的关键词
        keywords = self._extract_keywords(step_description)
        
        if not keywords:
            return ValidationResult(
                passed=False,
                confidence=0.3,
                reason="无法从步骤描述中提取关键词",
            )

        matched = sum(1 for kw in keywords if kw in page_text)
        match_ratio = matched / len(keywords) if keywords else 0
        
        passed = match_ratio >= 0.6
        confidence = 0.5 + match_ratio * 0.4
        
        return ValidationResult(
            passed=passed,
            confidence=confidence,
            reason=f"关键词匹配: {matched}/{len(keywords)} ({match_ratio:.1%})",
        )

    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词。"""
        # 简单的关键词提取：按空格分割，过滤短词
        words = text.split()
        keywords = [w for w in words if len(w) >= 2]
        return keywords[:5]  # 限制数量
