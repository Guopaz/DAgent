"""自动从旧 agent.py 拆分生成；按职责维护。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple


if TYPE_CHECKING:
    from agent.memory import Memory


class TaskStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    ABORTED = "aborted"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class TaskPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DecisionType(Enum):
    ACTION = "action"
    WAIT = "wait"
    COMPLETE = "complete"
    RECOVER = "recover"
    ABORT = "abort"


class ActionType(Enum):
    CLICK = "click"
    INPUT = "input"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    LONG_PRESS = "long_press"
    BACK = "back"
    HOME = "home"
    WAIT = "wait"


class ElementType(Enum):
    BUTTON = "button"
    TEXT_FIELD = "text_field"
    SECURE_TEXT_FIELD = "secure_text_field"
    STATIC_TEXT = "static_text"
    CELL = "cell"
    IMAGE = "image"
    SWITCH = "switch"
    SLIDER = "slider"
    TABLE = "table"
    NAVIGATION_BAR = "navigation_bar"
    TAB_BAR = "tab_bar"
    SEARCH_FIELD = "search_field"
    ALERT = "alert"
    KEYBOARD = "keyboard"
    OTHER = "other"


class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


class PlatformType(Enum):
    IOS = "ios"
    ANDROID = "android"
    SIMULATOR = "simulator"
    OTHER = "other"


class AgentRunState(Enum):
    INIT = "init"
    OBSERVING = "observing"
    PLANNING = "planning"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PROGRESS_UPDATED = "progress_updated"
    RECOVERING = "recovering"
    TASK_COMPLETED = "task_completed"
    FAILED = "failed"


class ValidationLevel(Enum):
    ACTION = "action"
    STATE = "state"
    GOAL = "goal"


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


class RecoveryStrategy(Enum):
    RETRY = "retry"
    SKIP_STEP = "skip"
    REPLAN = "re_decide"
    FALLBACK = "fallback"
    ABORT_TASK = "abort"
    RESTART_APP = "restart_app"
    GO_HOME = "go_home"


@dataclass
class Rect:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def center(self) -> Tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2


@dataclass
class UIElement:
    id: str
    type: ElementType = ElementType.OTHER
    text: str = ""
    label: str = ""
    value: str = ""
    visible: bool = True
    enabled: bool = True
    clickable: bool = False
    frame: Rect = field(default_factory=Rect)
    attributes: Dict[str, str] = field(default_factory=dict)

    @property
    def semantic_text(self) -> str:
        # WDA/Accessibility 中 text、label、value、name 经常重复，
        # 例如 name=Send label=发送 text=Send 会显示成 “Send 发送 Send”。
        # 这里仅做字段级去重，保留顺序，避免日志和 target 里出现重复元素名。
        parts: list[str] = []
        seen: set[str] = set()
        for raw in [self.text, self.label, self.value, self.attributes.get("name", "")]:
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            parts.append(value)
        return " ".join(parts).strip()

    @property
    def name(self) -> str:
        return self.attributes.get("name", "")

    @property
    def center(self) -> Tuple[float, float]:
        return self.frame.center

    @property
    def bounds(self) -> Dict[str, float]:
        return {"x": self.frame.x, "y": self.frame.y, "width": self.frame.width, "height": self.frame.height}

    def detail_dict(self) -> Dict[str, Any]:
        cx, cy = self.center
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "text": self.text,
            "label": self.label,
            "value": self.value,
            "visible": self.visible,
            "enabled": self.enabled,
            "clickable": self.clickable,
            "center": {"x": cx, "y": cy},
            "bounds": self.bounds,
            "attributes": self.attributes,
        }


@dataclass
class DeviceStatus:
    connection: ConnectionState = ConnectionState.UNKNOWN
    is_locked: bool = False
    foreground_app: str = ""
    target_app_foreground: bool = True
    screen_on: bool = True
    network_reachable: bool = True
    battery_level: float = -1.0
    orientation: str = "portrait"
    healthy: bool = True
    message: str = ""


@dataclass
class DeviceInfo:
    device_id: str = "unknown"
    platform: PlatformType = PlatformType.IOS
    model: str = "unknown"
    os_version: str = "unknown"
    screen_resolution: Tuple[int, int] = (0, 0)
    pixel_ratio: float = 1.0
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreenCapture:
    screenshot_path: str = ""
    ui_tree: List[UIElement] = field(default_factory=list)
    raw_ui_tree: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OperationResult:
    success: bool
    message: str = ""
    raw_response: Any = None
    duration: float = 0.0


@dataclass
class ObservationDiff:
    added: List[UIElement] = field(default_factory=list)
    removed: List[UIElement] = field(default_factory=list)
    changed: List[UIElement] = field(default_factory=list)
    page_changed: bool = False
    is_loading: bool = False
    has_alert: bool = False
    has_keyboard: bool = False


@dataclass
class Observation:
    page_name: str = "unknown"
    elements: List[UIElement] = field(default_factory=list)
    screenshot_path: str = ""
    raw_ui_tree: Any = None
    device_status: DeviceStatus = field(default_factory=DeviceStatus)
    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    page_metadata: Dict[str, Any] = field(default_factory=dict)
    available_actions: List[str] = field(default_factory=list)
    diff_from_previous: ObservationDiff = field(default_factory=ObservationDiff)

    def text_snapshot(self, max_items: Optional[int] = None, visible_only: bool = True) -> str:
        lines: list[str] = []
        source = [e for e in self.elements if (e.visible or not visible_only)]
        if max_items is not None:
            source = source[:max_items]
        for i, el in enumerate(source, 1):
            text = el.semantic_text
            if not text and el.type == ElementType.OTHER:
                continue
            cx, cy = el.center
            bounds = f"x={el.frame.x:.0f},y={el.frame.y:.0f},w={el.frame.width:.0f},h={el.frame.height:.0f}"
            lines.append(
                f"{i}. type={el.type.value} name='{el.name}' label='{el.label}' "
                f"text='{el.text}' value='{el.value}' visible={el.visible} enabled={el.enabled} "
                f"clickable={el.clickable} center=({cx:.0f},{cy:.0f}) bounds=({bounds})"
            )
        return "\n".join(lines) or "当前 UI 树未提供有效可见元素"

    def visible_element_details(self) -> List[Dict[str, Any]]:
        return [e.detail_dict() for e in self.elements if e.visible]


@dataclass
class Action:
    type: ActionType
    target: str = ""
    value: str = ""
    # 执行阶段使用的确定性 UI 元素引用，来自当前 Observation.elements[].id。
    # target 仅作为人类可读日志/兼容旧决策，不再作为主要模糊定位依据。
    element_id: str = ""


@dataclass
class NextDecision:
    type: DecisionType
    reason: str = ""
    action: Optional[Action] = None
    expected_outcome: str = ""
    progress_update: List[str] = field(default_factory=list)
    validation_hint: str = ""
    validation: Optional["LLMValidation"] = None  # LLM 对"上一步动作"的验证结果
    # LLM 在决策前对当前页面内容/状态的简短总结，用于日志展示。
    page_summary: str = ""


@dataclass
class ActionRecord:
    action: Action
    device_method: str
    parameters: Dict[str, Any]
    result: OperationResult
    screenshot_after: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0



@dataclass
class LLMValidation:
    """LLM 对"上一步动作"的验证结果"""
    passed: bool
    reason: str
    observation_summary: str = ""

@dataclass
class ValidationResult:
    passed: bool
    level: ValidationLevel = ValidationLevel.ACTION
    message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProgressRecord:
    round_index: int
    focus: str
    decision: NextDecision
    action_record: Optional[ActionRecord]
    validation: ValidationResult
    observation_before: Observation
    observation_after: Observation
    duration: float
    error: str = ""


@dataclass
class TaskMetrics:
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    action_count: int = 0
    failure_count: int = 0
    recovery_count: int = 0

    @property
    def duration(self) -> float:
        if not self.started_at:
            return 0.0
        return (self.ended_at or time.time()) - self.started_at


@dataclass
class TaskProgress:
    completed_objectives: List[str] = field(default_factory=list)
    pending_hints: List[str] = field(default_factory=list)
    current_focus: str = "初始化"
    action_count: int = 0
    last_decision: Optional[NextDecision] = None
    confidence: float = 0.0


@dataclass
class TaskGoal:
    description: str
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    max_actions: int = 30
    timeout: float = 600.0


@dataclass
class Task:
    goal: str
    params: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.CREATED
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    progress: TaskProgress = field(default_factory=TaskProgress)
    results: List[ProgressRecord] = field(default_factory=list)
    metrics: TaskMetrics = field(default_factory=TaskMetrics)


@dataclass
class ExecutionContext:
    task_goal: TaskGoal
    progress: TaskProgress
    observation: Observation
    device_status: DeviceStatus
    device_info: DeviceInfo
    memory: Memory
    state: AgentRunState


@dataclass
class ErrorInfo:
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.LOW
    code: str = ""
    message: str = ""
    context: str = ""
    timestamp: float = field(default_factory=time.time)
    suggested_strategy: RecoveryStrategy = RecoveryStrategy.REPLAN


@dataclass
class AgentState:
    task_id: str = ""
    task_status: TaskStatus = TaskStatus.CREATED
    task_goal: Optional[TaskGoal] = None
    progress: TaskProgress = field(default_factory=TaskProgress)
    current_round: int = 0
    current_node: str = "init"
    last_observation: Optional[Observation] = None
    device_status: DeviceStatus = field(default_factory=DeviceStatus)
    device_info: DeviceInfo = field(default_factory=DeviceInfo)
    last_decision: Optional[NextDecision] = None
    last_error: Optional[ErrorInfo] = None
    total_recoveries: int = 0
    consecutive_recoveries: int = 0
    started_at: float = 0.0
    last_active_at: float = field(default_factory=time.time)


@dataclass
class AgentStats:
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    completed_objectives: int = 0
    decision_rounds: int = 0
    failed_rounds: int = 0
    recovery_attempts: int = 0
    recovery_success_rate: float = 1.0
    screenshot_count: int = 0
    llm_call_duration: float = 0.0
    llm_token_usage: int = 0
    device_call_duration: float = 0.0

    @property
    def action_success_rate(self) -> float:
        return self.successful_actions / self.total_actions if self.total_actions else 1.0




@dataclass
class ActionContext:
    """上一步动作的上下文，用于 LLM 验证"""
    action_type: str
    action_target: str
    action_value: str
    page_before: str
    expected_outcome: str
    execution_result: str  # "success" | "failed" | "unknown"
