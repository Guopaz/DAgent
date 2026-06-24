"""自动从旧 agent.py 拆分生成；按职责维护。"""

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
from agent.helpers import _extract_json, _extract_search_keyword, _extract_after_keywords, _goal_tokens, _loose_contains, _safe_asdict, visible_element_details, find_best_element, first_element

class Planner:
    """滚动式下一步决策器。优先使用 LLM，失败时使用规则降级。"""

    def __init__(self, llm: Any = None):
        self.llm = llm

    def decide(self, context: ExecutionContext) -> NextDecision:
        if not context.device_status.healthy:
            return NextDecision(DecisionType.RECOVER, reason=f"设备状态不可用：{context.device_status.message}")
        if context.observation.diff_from_previous.is_loading:
            return NextDecision(DecisionType.WAIT, reason="页面处于加载状态", expected_outcome="等待页面稳定")
        if self._looks_done(context):
            return NextDecision(DecisionType.COMPLETE, reason="当前页面/历史进度已满足任务目标", progress_update=[context.task_goal.description])
        if self.llm:
            try:
                decision = self._llm_decide(context)
                if decision.type == DecisionType.COMPLETE and self._is_premature_complete(context):
                    return self._heuristic_decide(
                        context,
                        fallback_reason="LLM 提前判断完成，但该任务需要先执行动作，改用规则继续决策",
                    )
                return decision
            except Exception as exc:
                return self._heuristic_decide(context, fallback_reason=f"LLM 决策失败，启用规则降级：{exc}")
        return self._heuristic_decide(context)

    def _llm_decide(self, context: ExecutionContext) -> NextDecision:
        system = (
            "你是移动端自动化 Agent 的 Planner。你只负责输出下一步决策，不要生成完整计划。"
            "每次决策前，先用一句话简短总结当前页面、主要内容和任务相关状态。"
            "必须返回严格 JSON，格式："
            "{\"type\":\"action|wait|complete|recover|abort\",\"page_summary\":\"一句话页面/内容/状态总结\",\"reason\":\"...\"," 
            "\"action\":{\"type\":\"click|input|swipe_up|swipe_down|back|home|wait\",\"target\":\"UI树中的元素名/人类可读目标\",\"element_id\":\"ui_elements里的id，click必须填写\",\"value\":\"参数\"},"
            "\"expected_outcome\":\"...\",\"progress_update\":[\"...\"],\"validation_hint\":\"...\"}。"
            "page_summary 要客观简短，例如：当前是消息列表页，能看到刘泽东会话；或当前是聊天页，输入框和发送按钮可见。"
            "如果 action.type=click，必须从 visible_element_details 中选择一个当前存在的元素，填写其 id 到 element_id，target 填该元素的 name/text/label，禁止填写泛化描述。"
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
        return NextDecision(
            type=dtype,
            reason=str(data.get("reason", "")),
            action=action,
            expected_outcome=str(data.get("expected_outcome", "")),
            progress_update=list(data.get("progress_update") or []),
            validation_hint=str(data.get("validation_hint", "")),
            page_summary=str(data.get("page_summary", "")),
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

        执行阶段不再解释“底部导航栏消息标签/某人的对话条目”等自然语言，
        这里只接受当前 observation 里的 element_id；没有 id 时，仅允许 target 与
        UI 元素的 name/text/label/value/semantic_text 完全一致且唯一。
        """
        candidates = [e for e in context.observation.elements if e.visible and e.enabled]
        if action.element_id:
            matched = next((e for e in candidates if e.id == action.element_id), None)
            if not matched:
                raise ValueError(f"click 决策引用了不存在的 element_id={action.element_id}")
            action.target = Planner._element_display_text(matched) or action.target
            return action

        target = (action.target or "").strip()
        exact_matches = [
            e for e in candidates
            if target and target in {e.name, e.text, e.label, e.value, e.semantic_text}
        ]
        if len(exact_matches) == 1:
            matched = exact_matches[0]
            action.element_id = matched.id
            action.target = Planner._element_display_text(matched) or action.target
            return action
        if len(exact_matches) > 1:
            raise ValueError(f"click target={target!r} 对应多个 UI 元素，必须输出 element_id")
        raise ValueError("click 决策必须填写当前 UI 树里的 element_id，不能只填写自然语言 target")

    def _heuristic_decide(self, context: ExecutionContext, fallback_reason: str = "规则决策") -> NextDecision:
        goal = context.task_goal.description
        obs = context.observation
        lower_goal = goal.lower()

        # 目标中包含“打开/启动 App”，并能从常见 app 名推断 bundle id 时，优先点击桌面图标或让用户后续通过 WDA app 生命周期扩展。
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
                )

        if any(k in lower_goal for k in ["搜索", "查找", "找到"]) and "swipe_up" in obs.available_actions:
            return NextDecision(
                DecisionType.ACTION,
                reason=f"{fallback_reason}；当前未找到明确目标，滚动查看更多内容",
                action=Action(ActionType.SWIPE_UP, target="列表"),
                expected_outcome="列表展示更多候选项",
                validation_hint="验证页面元素发生变化",
            )

        return NextDecision(DecisionType.WAIT, reason=f"{fallback_reason}；信息不足，等待后重新观察", expected_outcome="页面稳定或出现新元素")

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
        if not cls._is_action_required_goal(goal):
            return False
        return context.progress.action_count == 0 and not context.progress.completed_objectives

    @classmethod
    def _looks_done(cls, context: ExecutionContext) -> bool:
        goal = context.task_goal.description
        criteria = context.task_goal.success_criteria or [goal]
        page_text = " ".join(e.semantic_text for e in context.observation.elements)
        history = " ".join(context.progress.completed_objectives)

        # 对“点击地图 / 返回上一页 / 输入xxx”这类命令式任务，
        # 页面上出现目标词（如“地图”）只说明目标可见，不代表动作已经完成。
        # 必须至少有执行动作或进度证据，才能进入完成判断。
        if cls._is_premature_complete(context):
            return False

        if cls._is_action_required_goal(goal):
            progress_evidence = history
            if not progress_evidence:
                return False
            return bool(criteria and all(_loose_contains(progress_evidence, c) for c in criteria))

        evidence = page_text + " " + history
        # 保守判断：只有出现明显完成词，或全部成功标准关键词都有证据，才完成。
        done_words = ["完成", "成功", "已投递", "已发送", "提交成功", "保存成功"]
        if any(w in evidence for w in done_words) and any(w in goal for w in ["投递", "发送", "提交", "保存", "完成"]):
            return True
        return bool(criteria and all(_loose_contains(evidence, c) for c in criteria))


