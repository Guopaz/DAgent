"""状态机管理 — 约束 Agent 在每个阶段允许的行为。"""

from __future__ import annotations

from agent.models import AgentPhase
from agent.state.state import State


class StateMachine:
    """状态机 — 确保 Agent 按正确顺序执行各阶段。"""

    VALID_TRANSITIONS = {
        AgentPhase.INIT: [AgentPhase.OBSERVING],
        AgentPhase.OBSERVING: [AgentPhase.PLANNING, AgentPhase.RECOVERING],
        AgentPhase.PLANNING: [AgentPhase.EXECUTING],
        AgentPhase.EXECUTING: [AgentPhase.VALIDATING],
        AgentPhase.VALIDATING: [
            AgentPhase.OBSERVING,  # 继续循环
            AgentPhase.STEP_COMPLETED,  # 步骤完成
            AgentPhase.RECOVERING,  # 验证失败
        ],
        AgentPhase.RECOVERING: [AgentPhase.OBSERVING, AgentPhase.TASK_COMPLETED],
        AgentPhase.STEP_COMPLETED: [AgentPhase.OBSERVING, AgentPhase.TASK_COMPLETED],
        AgentPhase.TASK_COMPLETED: [],
    }

    def __init__(self):
        self.state = State()

    def transition(self, target_phase: AgentPhase) -> bool:
        """尝试转换到目标阶段。"""
        current = self.state.get_phase()
        valid_targets = self.VALID_TRANSITIONS.get(current, [])

        if target_phase in valid_targets:
            self.state.set_phase(target_phase)
            return True
        
        return False

    def force_transition(self, target_phase: AgentPhase) -> None:
        """强制转换到目标阶段（用于异常恢复）。"""
        self.state.set_phase(target_phase)

    def get_phase(self) -> AgentPhase:
        """获取当前阶段。"""
        return self.state.get_phase()

    def can_transition(self, target_phase: AgentPhase) -> bool:
        """检查是否可以转换到目标阶段。"""
        current = self.state.get_phase()
        valid_targets = self.VALID_TRANSITIONS.get(current, [])
        return target_phase in valid_targets
