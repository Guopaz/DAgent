"""Agent 包 — 基于 WDA 的 iOS 自动化 Agent。"""

from agent.models import (
    Action,
    ActionRecord,
    ActionType,
    AgentPhase,
    AgentState,
    AgentStats,
    ElementType,
    ErrorCategory,
    ErrorInfo,
    ErrorSeverity,
    Observation,
    ObservationDiff,
    Plan,
    PlanStep,
    PreCheckResult,
    Rect,
    RecoveryStrategy,
    StepResult,
    TaskSnapshot,
    TaskStatus,
    UIElement,
    ValidationResult,
    WorkflowStatus,
)
from agent.executor.executor import Executor
from agent.loop import AgentLoop, PerceptionLayer
from agent.memory.memory import Memory
from agent.planner.planner import Planner
from agent.recovery.recovery_manager import RecoveryManager
from agent.task.task import Task
from agent.validator.validator import Validator

__all__ = [
    # 主循环与感知
    "AgentLoop",
    "PerceptionLayer",
    # 各模块
    "Executor",
    "Memory",
    "Planner",
    "RecoveryManager",
    "Validator",
    # 任务
    "Task",
    # 数据模型
    "Action",
    "ActionRecord",
    "ActionType",
    "AgentPhase",
    "AgentState",
    "AgentStats",
    "ElementType",
    "ErrorCategory",
    "ErrorInfo",
    "ErrorSeverity",
    "Observation",
    "ObservationDiff",
    "Plan",
    "PlanStep",
    "PreCheckResult",
    "Rect",
    "RecoveryStrategy",
    "StepResult",
    "TaskSnapshot",
    "TaskStatus",
    "UIElement",
    "ValidationResult",
    "WorkflowStatus",
]
