"""状态模型 — Agent 状态机阶段定义。"""

from __future__ import annotations

from agent.models import AgentPhase


class State:
    """状态模型 — 封装 Agent 当前阶段。"""

    def __init__(self):
        self.phase = AgentPhase.INIT

    def set_phase(self, phase: AgentPhase) -> None:
        """设置当前阶段。"""
        self.phase = phase

    def get_phase(self) -> AgentPhase:
        """获取当前阶段。"""
        return self.phase

    def is_observing(self) -> bool:
        return self.phase == AgentPhase.OBSERVING

    def is_planning(self) -> bool:
        return self.phase == AgentPhase.PLANNING

    def is_executing(self) -> bool:
        return self.phase == AgentPhase.EXECUTING

    def is_validating(self) -> bool:
        return self.phase == AgentPhase.VALIDATING

    def is_recovering(self) -> bool:
        return self.phase == AgentPhase.RECOVERING
