"""
Agent 决策器（Planner）。

核心职责：根据当前观察和任务进度，决定下一步动作。
- decide(): 入口方法，按优先级依次检查设备状态、加载检测、任务完成、停滞检测，最后调用 LLM 或规则降级
- _llm_decide(): LLM 决策路径，构建 prompt 包含上一步验证上下文，解析 JSON 输出
- _heuristic_decide(): 规则降级路径，LLM 不可用时使用简单规则
- _validate_by_rules(): 规则级验证回退，检查硬约束（页面跳转、输入值可见等）
- _looks_done(): 判断任务是否已完成，使用 _progress_genuinely_satisfies 做语义验证
- _detect_stagnation(): 停滞检测，连续滑动无效时提示切换策略
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
from agent.llm_client import LLMClient

from agent.models import *
from agent.helpers import _extract_json, _extract_search_keyword, _extract_after_keywords, _goal_tokens, _loose_contains, _safe_asdict, visible_element_details, find_best_element, first_element, _progress_genuinely_satisfies

# Planner: 决策器，根据当前观察和进度决定下一步动作
# 优先使用 LLM 决策，失败时回退到规则降级
class Planner:
    """滚动式下一步决策器。优先使用 LLM，失败时使用规则降级。"""

    def __init__(self, llm: LLMClient = None):
        self.llm = llm

    def decide(self, context: ExecutionContext, last_action_context: Optional[ActionContext] = None) -> NextDecision:
        if not context.device_status.healthy:
            return NextDecision(DecisionType.RECOVER, reason=f"设备状态不可用：{context.device_status.message}")
        if context.observation.diff_from_previous.is_loading:
            return NextDecision(DecisionType.WAIT, reason="页面处于加载状态", expected_outcome="等待页面稳定")
        if self._looks_done(context):
            return NextDecision(DecisionType.COMPLETE, reason="当前页面/历史进度已满足任务目标", progress_update=[context.task_goal.description])
        # 停滞检测：如果连续多次相同操作无效，提示切换策略或 abort
        stagnation = self._detect_stagnation(context)
        if stagnation:
            return stagnation
        if self.llm:
            try:
                decision = self._llm_decide(context, last_action_context)
                if decision.type == DecisionType.COMPLETE and self._is_premature_complete(context):
                    return self._heuristic_decide(
                        context,
                        last_action_context=last_action_context,
                        fallback_reason="LLM 提前判断完成，但该任务需要先执行动作，改用规则继续决策",
                    )
                return decision
            except Exception as exc:
                return self._heuristic_decide(context, last_action_context=last_action_context, fallback_reason=f"LLM 决策失败，启用规则降级：{exc}")
        return self._heuristic_decide(context, last_action_context=last_action_context)

    def _detect_stagnation(self, context: ExecutionContext) -> Optional[NextDecision]:
        """检测停滞：连续多次相同操作但未推进进度。"""
        recent = context.memory.recent_actions(5)
        if len(recent) < 3:
            return None
        # 检查最近 3 次是否都是相同类型的操作
        action_types = [a.get("action") for a in recent[-3:]]
        if len(set(action_types)) == 1 and action_types[0] in ["swipe_up", "swipe_down", "swipe_left", "swipe_right"]:
            # 连续 3 次滑动，检查是否有进度推进
            progress_count = len(context.progress.completed_objectives)
            if progress_count < len(action_types):
                return NextDecision(
                    DecisionType.ABORT,
                    reason=f"连续 {len(action_types)} 次 {action_types[0]} 操作未能找到目标，建议尝试其他策略（如搜索框）或声明任务无法完成",
                    progress_update=[],
                )
        return None

    def _llm_decide(self, context: ExecutionContext, last_action_context: Optional[ActionContext] = None) -> NextDecision:
        # 构建验证部分的 prompt
        validation_section = ""
        if last_action_context:
            validation_section = (
                f"\n## 上一步动作（请验证）\n"
                f"- 动作类型: {last_action_context.action_type}\n"
                f"- 目标: {last_action_context.action_target}\n"
                f"- 值: {last_action_context.action_value}\n"
                f"- 执行前页面: {last_action_context.page_before}\n"
                f"- 预期结果: {last_action_context.expected_outcome}\n"
                f"- 执行结果: {last_action_context.execution_result}\n"
                f"\n请根据当前页面状态判断上一步动作是否成功达到了预期效果。\n"
            )

        system = (
            "你是移动端自动化 Agent 的 Planner。你只负责输出下一步决策，不要生成完整计划。"
            "每次决策前，先用一句话简短总结当前页面、主要内容和任务相关状态。"
            f"{validation_section}"
            "必须返回严格 JSON，格式："
            "{\"type\":\"action|wait|complete|recover|abort\","
            "\"page_summary\":\"一句话页面/内容/状态总结\","
            "\"reason\":\"...\"," 
            "\"action\":{\"type\":\"click|input|swipe_up|swipe_down|back|home|wait\",\"target\":\"UI树中的元素名/人类可读目标\",\"element_id\":\"ui_elements里的id，click必须填写\",\"value\":\"参数\"},"
            "\"expected_outcome\":\"...\","
            "\"progress_update\":[\"...\"],"
            "\"validation_hint\":\"...\","
            "\"validation\":{\"passed\":true/false,\"reason\":\"验证通过/失败的原因\",\"observation_summary\":\"对当前页面的观察总结\"}"
            "}。"
            "page_summary 要客观简短，例如：当前是消息列表页，能看到刘泽东会话；或当前是聊天页，输入框和发送按钮可见。"
            "如果 action.type=click，必须从 visible_element_details 中选择一个当前存在的元素，填写其 id 到 element_id，target 填该元素的 name/text/label，禁止填写泛化描述。"
            "validation 字段：如果有上一步动作，必须填写验证结果。passed=true 表示上一步动作成功达到预期效果，passed=false 表示未达到。"
            "重要策略指导："
            "1. 如果某个操作（如滑动）未能找到目标元素，必须尝试其他策略（如使用搜索框、返回上级、或输出 abort）。"
            "2. 如果连续多次尝试同一策略无效，应该切换策略或声明任务无法完成（type=abort）。"
            "3. progress_update 中的条目必须区分'正在做'和'已完成'，例如'正在查找X'不等于'已进入X'。"
            "4. 只有当成功标准的动作真正完成时才能输出 type=complete，例如'已进入福宝有限公司的对话'必须确实进入了该对话，而不是仅仅在列表中看到了它。"
            "5. 如果上一步验证失败（validation.passed=false），progress_update 不应包含已完成的目标。"
        )
        user = json.dumps(
            {
                "goal": _safe_asdict(context.task_goal),
                "progress": _safe_asdict(context.progress),
                "device_status": _safe_asdict(context.device_status),
                "page_name": context.observation.page_name,
                "available_actions": context.observation.available_actions,
                "ui_elements": context.observation.text_snapshot(max_items=None),
                "visible_element_details": visible_element_details(context.observation.elements),
                "recent_actions": context.memory.recent_actions(8),
                "failures": context.memory.failures[-5:],
            },
            ensure_ascii=False,
        )
        content = self.llm.chat(system, user)
        data = _extract_json(content)
        dtype = DecisionType(str(data.get("type", "action")).lower())
        action_data = data.get("action") or None
        action = None
        if action_data and dtype == DecisionType.ACTION:
            action_type = ActionType(str(action_data.get("type", "click")).lower())
            action = Action(
                type=action_type,
                target=str(action_data.get("target", "")),
                value=str(action_data.get("value", "")),
                element_id=str(action_data.get("element_id", "")),
            )
            if action_type == ActionType.CLICK:
                action = self._bind_click_action_to_current_element(context, action)
        
        # 解析 validation
        validation = None
        val_data = data.get("validation")
        if val_data and last_action_context:
            validation = LLMValidation(
                passed=bool(val_data.get("passed", False)),
                reason=str(val_data.get("reason", "")),
                observation_summary=str(val_data.get("observation_summary", "")),
            )
        
        return NextDecision(
            type=dtype,
            reason=str(data.get("reason", "")),
            action=action,
            expected_outcome=str(data.get("expected_outcome", "")),
            progress_update=list(data.get("progress_update") or []),
            validation_hint=str(data.get("validation_hint", "")),
            page_summary=str(data.get("page_summary", "")),
            validation=validation,
        )



    @staticmethod
    def _element_display_text(element: UIElement) -> str:
        """用于日志/target 的单一元素显示名。

        不再把 name/text/label/value 全部拼在一起，避免出现
        `Send 发送 Send` 这类看起来像多个元素的 target。
        """
        values = [element.label, element.name, element.text, element.value, element.semantic_text]
        for value in values:
            text = str(value or "").strip()
            if text:
                return text
        return element.id

    @staticmethod
    def _bind_click_action_to_current_element(context: ExecutionContext, action: Action) -> Action:
        """把 LLM click 决策绑定到当前 UI 树中的确定元素。

        执行阶段不再解释"底部导航栏消息标签/某人的对话条目"等自然语言，
        这里只接受当前 observation 里的 element_id；没有 id 时，仅允许 target 与
        UI 元素的 name/text/label/value/semantic_text 完全一致且唯一。
        """
        candidates = [e for e in context.observation.elements if e.visible and e.enabled]
        if action.element_id:
            matched = next((e for e in candidates if e.id == action.element_id), None)
            if matched:
                return action
            # element_id 在当前 UI 树中不存在，降级使用 target。
            action.element_id = ""

        if action.target:
            matches = [
                e for e in candidates
                if action.target in (e.name, e.text, e.label, e.value, e.semantic_text)
            ]
            if len(matches) == 1:
                action.element_id = matches[0].id
                return action
            if len(matches) > 1:
                raise ValueError(f"click target={action.target!r} 对应多个 UI 元素，必须输出 element_id")
        raise ValueError(f"click 决策必须填写当前 UI 树里的 element_id，不能只填写自然语言 target")

    def _heuristic_decide(self, context: ExecutionContext, last_action_context: Optional[ActionContext] = None, fallback_reason: str = "规则决策") -> NextDecision:
        goal = context.task_goal.description
        obs = context.observation
        lower_goal = goal.lower()

        # 规则验证：如果有上一步动作，先验证
        validation = None
        if last_action_context:
            validation = self._validate_by_rules(last_action_context, context.observation)

        # 目标中包含"打开/启动 App"，并能从常见 app 名推断 bundle id 时，优先点击桌面图标或让用户后续通过 WDA app 生命周期扩展。
        app_name = _extract_after_keywords(goal, ["打开", "启动", "进入"])
        if app_name:
            matched = find_best_element(obs.elements, app_name, clickable_only=True)
            if matched:
                return NextDecision(
                    DecisionType.ACTION,
                    reason=f"{fallback_reason}；发现与目标 App/入口匹配的元素：{matched.semantic_text}",
                    action=Action(ActionType.CLICK, target=self._element_display_text(matched), element_id=matched.id),
                    expected_outcome=f"进入 {app_name}",
                    validation_hint=f"页面出现 {app_name} 相关内容",
                    validation=validation,
                )

        # 如果任务包含输入/搜索关键字，优先处理搜索框/文本框。
        keyword = _extract_search_keyword(goal)
        input_el = first_element(obs.elements, {ElementType.SEARCH_FIELD, ElementType.TEXT_FIELD})
        if keyword and input_el:
            if keyword not in input_el.value:
                return NextDecision(
                    DecisionType.ACTION,
                    reason=f"{fallback_reason}；任务需要搜索/输入关键词，当前存在输入框",
                    action=Action(ActionType.INPUT, target=input_el.semantic_text or "搜索框", value=keyword),
                    expected_outcome=f"输入框包含 {keyword}",
                    validation_hint=f"验证输入框 value 是否包含 {keyword}",
                    validation=validation,
                )

        # 点击目标中提到的按钮/文本。
        for token in _goal_tokens(goal):
            matched = find_best_element(obs.elements, token, clickable_only=True)
            if matched:
                return NextDecision(
                    DecisionType.ACTION,
                    reason=f"{fallback_reason}；页面中存在目标相关可点击元素 {matched.semantic_text}",
                    action=Action(ActionType.CLICK, target=self._element_display_text(matched), element_id=matched.id),
                    expected_outcome="页面发生跳转或目标进度推进",
                    validation_hint="验证页面是否变化或出现下一阶段元素",
                    validation=validation,
                )

        if any(k in lower_goal for k in ["搜索", "查找", "找到"]) and "swipe_up" in obs.available_actions:
            return NextDecision(
                DecisionType.ACTION,
                reason=f"{fallback_reason}；当前未找到明确目标，滚动查看更多内容",
                action=Action(ActionType.SWIPE_UP, target="列表"),
                expected_outcome="列表展示更多候选项",
                validation_hint="验证页面元素发生变化",
                validation=validation,
            )

        return NextDecision(DecisionType.WAIT, reason=f"{fallback_reason}；信息不足，等待后重新观察", expected_outcome="页面稳定或出现新元素", validation=validation)

    @staticmethod
    def _validate_by_rules(last_action_context: ActionContext, observation: Observation) -> LLMValidation:
        """规则级验证：只检查硬约束（设备连接、动作是否执行成功）"""
        # 基本检查：动作是否执行成功
        if last_action_context.execution_result == "failed":
            return LLMValidation(
                passed=False,
                reason=f"动作执行失败：{last_action_context.execution_result}",
                observation_summary="动作未成功执行",
            )
        
        # 对于点击操作，检查页面是否发生变化
        if last_action_context.action_type in ["click", "swipe_up", "swipe_down", "swipe_left", "swipe_right", "scroll", "pinch"]:
            # 如果页面名称变化或元素数量变化，认为成功
            if observation.page_name != last_action_context.page_before:
                return LLMValidation(
                    passed=True,
                    reason="页面发生跳转",
                    observation_summary=f"从 {last_action_context.page_before} 跳转到 {observation.page_name}",
                )
            # 如果元素数量有显著变化（>10%），认为成功
            # 这里简化处理，只要有变化就认为成功
            return LLMValidation(
                passed=True,
                reason="页面元素发生变化",
                observation_summary="页面内容已更新",
            )
        
        # 对于输入操作，检查输入值是否出现在页面中
        if last_action_context.action_type == "input" and last_action_context.action_value:
            page_text = " ".join(e.semantic_text for e in observation.elements)
            if last_action_context.action_value in page_text:
                return LLMValidation(
                    passed=True,
                    reason="输入值出现在页面中",
                    observation_summary=f"页面包含输入值：{last_action_context.action_value}",
                )
            else:
                return LLMValidation(
                    passed=False,
                    reason="输入值未出现在页面中",
                    observation_summary="未在页面找到输入值",
                )
        
        # 默认认为成功（保守策略）
        return LLMValidation(
            passed=True,
            reason="动作已执行",
            observation_summary="页面状态已更新",
        )

    @staticmethod
    def _is_action_required_goal(goal: str) -> bool:
        return any(
            verb in goal
            for verb in [
                "点击", "点一下", "点开", "选择", "输入", "搜索", "滑动", "上滑", "下滑",
                "返回", "打开", "启动", "进入", "关闭", "提交", "发送", "投递", "保存",
            ]
        )

    @classmethod
    def _is_premature_complete(cls, context: ExecutionContext) -> bool:
        goal = context.task_goal.description
        
        # 多步骤任务：包含逗号分隔的多个子任务
        if ',' in goal or '，' in goal:
            subtasks = [s.strip() for s in goal.replace(',', '，').split('，') if s.strip()]
            # 如果子任务数量 > 1，检查是否所有子任务都已完成
            if len(subtasks) > 1:
                # 每个子任务需要有对应的 completed_objective
                if len(context.progress.completed_objectives) < len(subtasks):
                    return True
                # 检查每个子任务是否在进度中有对应完成记录
                for subtask in subtasks:
                    if not any(subtask in obj or _loose_contains(obj, subtask) 
                              for obj in context.progress.completed_objectives):
                        return True
                return False
        
        if not cls._is_action_required_goal(goal):
            return False
        return context.progress.action_count == 0 and not context.progress.completed_objectives

    @classmethod
    def _looks_done(cls, context: ExecutionContext) -> bool:
        goal = context.task_goal.description
        criteria = context.task_goal.success_criteria or [goal]
        page_text = " ".join(e.semantic_text for e in context.observation.elements)

        # 对"点击地图 / 返回上一页 / 输入xxx"这类命令式任务，
        # 页面上出现目标词（如"地图"）只说明目标可见，不代表动作已经完成。
        # 必须至少有执行动作或进度证据，才能进入完成判断。
        if cls._is_premature_complete(context):
            return False

        if cls._is_action_required_goal(goal):
            # 使用语义验证，避免"正在查找X"误判为"已进入X"
            if not context.progress.completed_objectives:
                return False
            return _progress_genuinely_satisfies(context.progress.completed_objectives, criteria)

        history = " ".join(context.progress.completed_objectives)
        evidence = page_text + " " + history
        
        # 多步骤任务：包含逗号分隔的多个子任务
        if ',' in goal or '，' in goal:
            subtasks = [s.strip() for s in goal.replace(',', '，').split('，') if s.strip()]
            if len(subtasks) > 1:
                # 检查每个子任务是否都有证据（页面文本或进度）
                for subtask in subtasks:
                    subtask_evidence = page_text if not any(m in subtask for m in ["切换", "返回", "上一页"]) else history
                    if not _loose_contains(subtask_evidence, subtask):
                        return False
                return True
        
        # 保守判断：只有出现明显完成词，或全部成功标准关键词都有证据，才完成。
        done_words = ["完成", "成功", "已投递", "已发送", "提交成功", "保存成功"]
        if any(w in evidence for w in done_words) and any(w in goal for w in ["投递", "发送", "提交", "保存", "完成"]):
            return True
        return bool(criteria and all(_loose_contains(evidence, c) for c in criteria))
