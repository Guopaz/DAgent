"""核心数据模型 — 所有模块共享的枚举、数据类和类型定义。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ============================================================
# 任务状态
# ============================================================

class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    ABORTED = "aborted"
    TIMED_OUT = "timed_out"


# ============================================================
# 元素类型
# ============================================================

class ElementType(Enum):
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    TEXT_VIEW = "text_view"
    IMAGE = "image"
    CELL = "cell"
    TABLE = "table"
    COLLECTION_VIEW = "collection_view"
    SCROLL_VIEW = "scroll_view"
    NAVIGATION_BAR = "navigation_bar"
    TAB_BAR = "tab_bar"
    SWITCH = "switch"
    SLIDER = "slider"
    ALERT = "alert"
    SHEET = "sheet"
    KEYBOARD = "keyboard"
    OTHER = "other"

    @classmethod
    def from_xcui(cls, xcui_type: str) -> ElementType:
        """从 XCUIElementType 字符串映射到 ElementType。"""
        mapping = {
            "XCUIElementTypeButton": cls.BUTTON,
            "XCUIElementTypeTextField": cls.TEXT_FIELD,
            "XCUIElementTypeSearchField": cls.TEXT_FIELD,
            "XCUIElementTypeSecureTextField": cls.TEXT_FIELD,
            "XCUIElementTypeTextView": cls.TEXT_VIEW,
            "XCUIElementTypeStaticText": cls.TEXT_VIEW,
            "XCUIElementTypeImage": cls.IMAGE,
            "XCUIElementTypeCell": cls.CELL,
            "XCUIElementTypeTable": cls.TABLE,
            "XCUIElementTypeCollectionView": cls.COLLECTION_VIEW,
            "XCUIElementTypeScrollView": cls.SCROLL_VIEW,
            "XCUIElementTypeNavigationBar": cls.NAVIGATION_BAR,
            "XCUIElementTypeTabBar": cls.TAB_BAR,
            "XCUIElementTypeSwitch": cls.SWITCH,
            "XCUIElementTypeSlider": cls.SLIDER,
            "XCUIElementTypeAlert": cls.ALERT,
            "XCUIElementTypeSheet": cls.SHEET,
            "XCUIElementTypeKeyboard": cls.KEYBOARD,
        }
        return mapping.get(xcui_type, cls.OTHER)


# ============================================================
# 几何模型
# ============================================================

@dataclass
class Rect:
    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


# ============================================================
# UI 元素
# ============================================================

@dataclass
class UIElement:
    id: str = ""
    type: ElementType = ElementType.OTHER
    text: str = ""
    label: str = ""
    value: str = ""
    visible: bool = True
    enabled: bool = True
    clickable: bool = False
    frame: Rect = field(default_factory=Rect)
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "text": self.text,
            "label": self.label,
            "value": self.value,
            "visible": self.visible,
            "enabled": self.enabled,
            "clickable": self.clickable,
            "frame": self.frame.to_dict(),
            "attributes": self.attributes,
        }


# ============================================================
# 观察 (Observation)
# ============================================================

@dataclass
class Observation:
    elements: List[UIElement] = field(default_factory=list)
    screenshot_base64: str = ""
    page_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_summary(self) -> str:
        """生成页面摘要文本。"""
        lines = [f"页面: {self.page_name or '未知'}"]
        lines.append(f"元素数: {len(self.elements)}")
        interactive = [e for e in self.elements if e.clickable and e.visible]
        if interactive:
            lines.append(f"可交互元素 ({len(interactive)}):")
            for e in interactive[:20]:
                desc = e.label or e.text or e.id
                lines.append(f"  - [{e.type.value}] {desc}")
        return "\n".join(lines)


# ============================================================
# 观察差异 (ObservationDiff)
# ============================================================

@dataclass
class ObservationDiff:
    added: List[UIElement] = field(default_factory=list)
    removed: List[UIElement] = field(default_factory=list)
    changed: List[UIElement] = field(default_factory=list)
    page_changed: bool = False
    has_alert: bool = False
    has_keyboard: bool = False
    is_loading: bool = False
    similarity: float = 1.0


# ============================================================
# 动作类型
# ============================================================

class ActionType(Enum):
    CLICK = "CLICK"
    INPUT = "INPUT"
    SCROLL = "SCROLL"
    SWIPE = "SWIPE"
    WAIT = "WAIT"
    BACK = "BACK"
    HOME = "HOME"
    LAUNCH_APP = "LAUNCH_APP"
    DISMISS_ALERT = "DISMISS_ALERT"
    DISMISS_KEYBOARD = "DISMISS_KEYBOARD"
    LONG_PRESS = "LONG_PRESS"
    NONE = "NONE"


# ============================================================
# 动作与动作记录
# ============================================================

@dataclass
class Action:
    action_type: ActionType = ActionType.NONE
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "reason": self.reason,
        }


@dataclass
class ToolResponse:
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionRecord:
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[ToolResponse] = None
    screenshot_after: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "result": {"success": self.result.success, "message": self.result.message} if self.result else None,
            "timestamp": self.timestamp,
            "duration": self.duration,
        }


# ============================================================
# 执行计划
# ============================================================

@dataclass
class PlanStep:
    index: int = 0
    description: str = ""
    status: str = "pending"  # pending / running / success / failed / skipped
    actions: List[ActionRecord] = field(default_factory=list)
    result_message: str = ""


@dataclass
class Plan:
    steps: List[PlanStep] = field(default_factory=list)
    raw_text: str = ""


# ============================================================
# 步骤结果
# ============================================================

@dataclass
class StepResult:
    step_index: int = 0
    success: bool = False
    message: str = ""
    actions_count: int = 0


# ============================================================
# 错误与恢复模型
# ============================================================

class ErrorCategory(Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    PAGE_NOT_EXPECTED = "page_not_expected"
    APP_CRASH = "app_crash"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorInfo:
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.LOW
    code: str = ""
    message: str = ""
    context: str = ""
    timestamp: float = field(default_factory=time.time)
    suggested_strategy: RecoveryStrategy = None  # forward ref, set after

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp,
            "suggested_strategy": self.suggested_strategy.value if self.suggested_strategy else None,
        }


class RecoveryStrategy(Enum):
    RETRY = "retry"
    SKIP_STEP = "skip"
    REPLAN = "replan"
    FALLBACK = "fallback"
    ABORT_TASK = "abort"
    RESTART_APP = "restart_app"
    GO_HOME = "go_home"


# 修复前向引用
ErrorInfo.__dataclass_fields__["suggested_strategy"].default = None


# ============================================================
# 工作流状态
# ============================================================

class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================
# Agent 状态机阶段
# ============================================================

class AgentPhase(Enum):
    INIT = "init"
    OBSERVING = "observing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    RECOVERING = "recovering"
    STEP_COMPLETED = "step_completed"
    TASK_COMPLETED = "task_completed"


# ============================================================
# 前置检查结果
# ============================================================

class PreCheckResult(Enum):
    NORMAL = "normal"
    HANDLED = "handled"
    WAIT = "wait"
    ABORT = "abort"


# ============================================================
# 验证结果
# ============================================================

@dataclass
class ValidationResult:
    passed: bool = False
    confidence: float = 0.0
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Agent 运行状态
# ============================================================

@dataclass
class AgentState:
    task_id: str = ""
    task_status: TaskStatus = TaskStatus.CREATED
    current_step_index: int = 0
    plan: Optional[Plan] = None
    last_observation: Optional[Observation] = None
    last_error: Optional[ErrorInfo] = None
    total_recoveries: int = 0
    consecutive_recoveries: int = 0
    started_at: float = field(default_factory=time.time)
    last_active_at: float = field(default_factory=time.time)


@dataclass
class AgentStats:
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    completed_steps: int = 0
    skipped_steps: int = 0
    failed_steps: int = 0
    recovery_attempts: int = 0
    recovery_successes: int = 0
    screenshot_count: int = 0
    llm_call_duration: float = 0.0
    llm_token_usage: int = 0
    wda_call_duration: float = 0.0

    @property
    def success_rate(self) -> float:
        if self.total_actions == 0:
            return 1.0
        return self.successful_actions / self.total_actions

    @property
    def recovery_success_rate(self) -> float:
        if self.recovery_attempts == 0:
            return 1.0
        return self.recovery_successes / self.recovery_attempts


# ============================================================
# 任务快照
# ============================================================

@dataclass
class TaskSnapshot:
    task_id: str = ""
    status: TaskStatus = TaskStatus.CREATED
    current_step_index: int = 0
    plan: Optional[Plan] = None
    results: List[StepResult] = field(default_factory=list)
    contexts: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


# ============================================================
# 健康检查项
# ============================================================

@dataclass
class HealthCheck:
    name: str = ""
    healthy: bool = True
    message: str = ""
    value: Any = None
    threshold: Any = None
