"""规划器 — 基于当前状态决策下一步动作。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from agent.models import Action, ActionType, Observation
from agent.planner.prompt import PLANNER_SYSTEM_PROMPT, PLANNER_USER_PROMPT

if TYPE_CHECKING:
    pass


class Planner:
    """规划器 — 使用 LLM 决定下一步动作。"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def plan(self, step_description: str, observation: Observation, action_history: str) -> Action:
        """基于观察结果规划下一步动作。"""
        page_name = observation.page_name or "未知页面"
        elements_list = self._format_elements(observation)
        metadata = json.dumps(observation.metadata, ensure_ascii=False) if observation.metadata else "{}"

        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            step_description=step_description,
            page_name=page_name,
            elements_list=elements_list,
            metadata=metadata,
            action_history=action_history or "无历史动作",
        )

        user_prompt = PLANNER_USER_PROMPT.format(
            step_description=step_description,
            page_name=page_name,
        )

        try:
            response = self.llm.chat(system_prompt, user_prompt)
            data = json.loads(response)
            return self._parse_action(data)
        except Exception as e:
            return Action(
                action_type=ActionType.WAIT,
                target="",
                parameters={"seconds": 2},
                reason=f"规划失败，等待重试: {e}",
            )

    def _format_elements(self, observation: Observation) -> str:
        """格式化可交互元素列表。"""
        elements = []
        for elem in observation.elements:
            if elem.clickable and elem.visible:
                desc = elem.label or elem.text or elem.id
                elements.append(f"- [{elem.type.value}] {desc}")
        
        if not elements:
            return "无可见可交互元素"
        
        return "\n".join(elements[:30])  # 限制数量避免过长

    def _parse_action(self, data: dict) -> Action:
        """解析 LLM 返回的动作数据。"""
        action_type_str = data.get("action", "NONE").upper()
        target = data.get("target", "")
        parameters = data.get("parameters", {})
        reason = data.get("reason", "")

        try:
            action_type = ActionType(action_type_str)
        except ValueError:
            action_type = ActionType.NONE
            reason += f" (未知动作类型: {action_type_str})"

        return Action(
            action_type=action_type,
            target=target,
            parameters=parameters,
            reason=reason,
        )
