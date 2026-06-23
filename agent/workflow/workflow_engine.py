"""工作流引擎 — 将任务目标分解为有序步骤。"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from agent.models import Plan, PlanStep
from agent.workflow.workflow import Workflow

if TYPE_CHECKING:
    from agent.task.task import Task


class WorkflowEngine:
    """工作流引擎 — 使用 LLM 将任务分解为步骤序列。"""

    def __init__(self, llm_client):
        self.llm = llm_client

    def create_workflow(self, task: Task) -> Workflow:
        """为任务创建工作流。"""
        plan = self._generate_plan(task.goal, task.params)
        workflow = Workflow(task_id=task.task_id, plan=plan)
        return workflow

    def _generate_plan(self, goal: str, params: dict) -> Plan:
        """使用 LLM 生成执行计划。"""
        prompt = f"""你是一个 iOS 自动化测试专家。请将以下任务分解为具体的执行步骤。

任务目标: {goal}
参数: {params}

要求:
1. 每个步骤应该是一个明确的、可执行的操作
2. 步骤之间应该有清晰的逻辑顺序
3. 步骤描述应该简洁但具体
4. 返回 JSON 格式: {{"steps": ["步骤1描述", "步骤2描述", ...]}}

只返回 JSON，不要其他内容。"""

        try:
            response = self.llm.chat(prompt)
            data = json.loads(response)
            step_descriptions = data.get("steps", [])
            
            steps = [
                PlanStep(index=i, description=desc, status="pending")
                for i, desc in enumerate(step_descriptions, 1)
            ]
            
            return Plan(steps=steps, raw_text=response)
        except Exception as e:
            # 降级：创建单步计划
            return Plan(
                steps=[PlanStep(index=1, description=goal, status="pending")],
                raw_text=f"Error generating plan: {e}",
            )
