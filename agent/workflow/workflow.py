"""工作流模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from agent.models import Plan, WorkflowStatus


@dataclass
class Workflow:
    task_id: str
    plan: Plan
    current_step_index: int = 0
    status: WorkflowStatus = WorkflowStatus.CREATED

    def start(self) -> None:
        """启动工作流。"""
        if self.status == WorkflowStatus.CREATED:
            self.status = WorkflowStatus.RUNNING

    def complete(self) -> None:
        """标记工作流完成。"""
        if self.status == WorkflowStatus.RUNNING:
            self.status = WorkflowStatus.COMPLETED

    def fail(self) -> None:
        """标记工作流失败。"""
        if self.status == WorkflowStatus.RUNNING:
            self.status = WorkflowStatus.FAILED

    def advance_step(self) -> None:
        """推进到下一步骤。"""
        if self.current_step_index < len(self.plan.steps) - 1:
            self.current_step_index += 1

    def is_finished(self) -> bool:
        """检查工作流是否结束。"""
        return self.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)

    def current_step(self):
        """获取当前步骤。"""
        if self.current_step_index < len(self.plan.steps):
            return self.plan.steps[self.current_step_index]
        return None
