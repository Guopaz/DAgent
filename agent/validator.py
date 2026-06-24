"""
Agent 验证器（Validator）。

核心职责：验证动作执行结果和任务完成状态。
- validate(): 动作验证入口，优先使用 LLM 验证结果（decision.validation），回退到规则验证
- validate_goal(): 任务完成验证，检查 success_criteria 是否全部满足
- 规则验证作为安全网：检查页面变化、输入值可见等硬约束
"""

from __future__ import annotations

import base64
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from agent.models import *
from agent.helpers import _is_navigation_back_goal, _loose_contains, _safe_asdict, _progress_genuinely_satisfies

# Validator: 验证器，验证动作执行结果和任务完成状态
# 优先使用 LLM 验证结果，回退到规则验证作为安全网
class Validator:
    """验证器：主要依赖 LLM 验证结果，规则验证作为安全网。"""

    def validate(
        self,
        decision: NextDecision,
        action_record: Optional[ActionRecord],
        before: Observation,
        after: Observation,
        task_goal: TaskGoal,
        progress: Optional[TaskProgress] = None,
        memory: Optional["Memory"] = None,
        llm_validation: Optional[LLMValidation] = None,
    ) -> ValidationResult:
        if decision.type == DecisionType.COMPLETE:
            return self.validate_goal(after, task_goal, progress=progress, memory=memory, llm_validation=llm_validation)
        if decision.type == DecisionType.WAIT:
            return ValidationResult(True, ValidationLevel.STATE, "等待完成，已重新观察", {"page_changed": after.diff_from_previous.page_changed})
        if decision.type != DecisionType.ACTION:
            return ValidationResult(True, ValidationLevel.STATE, f"非动作决策：{decision.type.value}")
        if not action_record:
            return ValidationResult(False, ValidationLevel.ACTION, "缺少动作记录")
        if not action_record.result.success:
            return ValidationResult(False, ValidationLevel.ACTION, action_record.result.message, {"record": _safe_asdict(action_record)})

        # 如果有 LLM 验证结果，优先使用
        if llm_validation:
            return ValidationResult(
                llm_validation.passed,
                ValidationLevel.STATE,
                f"LLM验证: {llm_validation.reason}",
                {"llm_validation": True, "observation_summary": llm_validation.observation_summary},
            )

        # 规则验证作为安全网
        action = action_record.action
        if action.type in {ActionType.CLICK, ActionType.SWIPE_UP, ActionType.SWIPE_DOWN, ActionType.BACK, ActionType.HOME}:
            changed = after.diff_from_previous.page_changed or before.page_name != after.page_name
            return ValidationResult(
                True,
                ValidationLevel.STATE,
                "动作已下发；页面变化检测结果：" + ("有变化" if changed else "无明显变化"),
                {"page_changed": changed},
            )
        if action.type == ActionType.INPUT:
            page_text = " ".join(e.semantic_text for e in after.elements)
            ok = bool(action.value and action.value in page_text)
            return ValidationResult(True, ValidationLevel.STATE, "输入动作已下发" + ("，页面可见输入值" if ok else "，未在 UI 树确认输入值"), {"value_seen": ok})
        return ValidationResult(True, ValidationLevel.ACTION, "动作已执行")

    def validate_goal(
        self,
        observation: Observation,
        task_goal: TaskGoal,
        progress: Optional[TaskProgress] = None,
        memory: Optional["Memory"] = None,
        llm_validation: Optional[LLMValidation] = None,
    ) -> ValidationResult:
        # 如果有 LLM 验证结果且 passed=true，直接信任 LLM 的判断
        if llm_validation and llm_validation.passed:
            return ValidationResult(
                True,
                ValidationLevel.GOAL,
                f"LLM验证通过: {llm_validation.reason}",
                {"llm_validation": True, "observation_summary": llm_validation.observation_summary},
            )
        text = " ".join(e.semantic_text for e in observation.elements)
        criteria = task_goal.success_criteria or [task_goal.description]
        matched = [c for c in criteria if _loose_contains(text, c)]
        if len(matched) == len(criteria):
            return ValidationResult(True, ValidationLevel.GOAL, "任务成功标准已满足", {"matched": matched, "source": "observation"})

        # 导航类任务（返回上一页/回到上一页）完成后的页面通常不会显示"返回上一页"字样，
        # 不能只用当前 UI 文本匹配成功标准。应结合最近动作和页面变化验证。
        if _is_navigation_back_goal(task_goal.description, criteria):
            nav_result = self._validate_navigation_back(progress=progress, memory=memory)
            if nav_result.passed:
                return nav_result

        # 对 LLM COMPLETE 采用保守策略：若页面有明显成功提示也通过。
        if any(w in text for w in ["完成", "成功", "已投递", "提交成功", "发送成功"]):
            return ValidationResult(True, ValidationLevel.GOAL, "页面出现成功提示", {"text_excerpt": text[:500]})

        # 对非导航任务，允许用已验证动作产生的进度作为辅助证据，但不能单靠 Planner 的 COMPLETE。
        if progress and memory and progress.completed_objectives and memory.action_history:
            successful_actions = [a for a in memory.action_history if a.get("success") and a.get("validation_passed")]
            if successful_actions and _progress_genuinely_satisfies(progress.completed_objectives, criteria):
                progress_text = " ".join(progress.completed_objectives)
                progress_matched = [c for c in criteria if _loose_contains(progress_text, c)]
                return ValidationResult(
                    True,
                    ValidationLevel.GOAL,
                    "任务成功标准已由已验证动作进度满足",
                    {"matched": progress_matched, "source": "progress+validated_actions", "last_action": successful_actions[-1]},
                )

        return ValidationResult(False, ValidationLevel.GOAL, "未能确认所有成功标准", {"matched": matched, "criteria": criteria})

    @staticmethod
    def _validate_navigation_back(progress: Optional[TaskProgress], memory: Optional["Memory"]) -> ValidationResult:
        if not memory:
            return ValidationResult(False, ValidationLevel.GOAL, "缺少 Memory，无法验证返回任务")

        page_changed = len(memory.page_history) >= 2 and memory.page_history[-1] != memory.page_history[-2]
        successful_nav_actions = []
        for item in memory.action_history:
            target = str(item.get("target", "")).lower()
            action = str(item.get("action", "")).lower()
            method = str(item.get("method", "")).lower()
            message = str(item.get("message", ""))
            is_nav_action = (
                action == "back"
                or method == "press_back"
                or "返回" in target
                or "back" in target
                or "leftback" in target
            )
            has_change_evidence = page_changed or "有变化" in message or "page_changed': True" in message
            if item.get("success") and item.get("validation_passed") and is_nav_action and has_change_evidence:
                successful_nav_actions.append(item)

        progress_text = " ".join(progress.completed_objectives) if progress else ""
        has_progress_evidence = any(k in progress_text for k in ["返回", "上一页", "上一级"])
        if successful_nav_actions:
            return ValidationResult(
                True,
                ValidationLevel.GOAL,
                "返回任务已由成功返回动作和页面变化确认",
                {
                    "source": "memory.action_history+page_history",
                    "last_navigation_action": successful_nav_actions[-1],
                    "page_history_tail": memory.page_history[-3:],
                    "progress_evidence": has_progress_evidence,
                },
            )
        return ValidationResult(
            False,
            ValidationLevel.GOAL,
            "未找到成功的返回动作及页面变化证据",
            {"page_changed": page_changed, "page_history_tail": memory.page_history[-3:]},
        )
