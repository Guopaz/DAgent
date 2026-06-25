"""
Agent 数据模型定义文件。

定义 Agent 系统中所有核心数据结构，分为以下几类：
- 枚举类型：TaskStatus, DecisionType, ActionType, ElementType, AgentRunState 等
- UI 模型：Rect, UIElement — WDA 解析后的 UI 元素
- 设备模型：DeviceStatus, DeviceInfo, ScreenCapture, OperationResult
- 观察模型：Observation, ObservationDiff — PerceptionLayer 的输出
- 决策模型：Action, NextDecision — Planner 的输出
- 验证模型：LLMValidation, ValidationResult, ActionContext — Validator 和 LLM 验证
- 执行模型：ActionRecord, ProgressRecord — 单轮执行记录
- 任务模型：Task, TaskGoal, TaskProgress, TaskMetrics — 任务定义与进度
- 上下文模型：ExecutionContext — Planner 决策时的完整上下文
- 状态模型：AgentState, AgentStats, ErrorInfo — 运行时状态与统计
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple


if TYPE_CHECKING:
    from agent.memory import Memory


# 任务生命周期状态
class TaskStatus(Enum):
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    PARTIAL = "partial"
    ABORTED = "aborted"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


# 任务优先级
class TaskPriority(Enum):
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


# Planner 决策类型
class DecisionType(Enum):
    """
    Planner 的决策输出。
    
    包含决策类型、理由、具体动作（如果有）、验证提示和进度更新。
    由 Planner 生成，Executor 执行，Validator 验证。
    """
    ACTION = "action"
    WAIT = "wait"
    COMPLETE = "complete"
    RECOVER = "recover"
    ABORT = "abort"


# 可执行的动作类型
class ActionType(Enum):
    CLICK = "click"
    INPUT = "input"
    SWIPE_UP = "swipe_up"
    SWIPE_DOWN = "swipe_down"
    SWIPE_LEFT = "swipe_left"
    SWIPE_RIGHT = "swipe_right"
    SCROLL = "scroll"
    DRAG = "drag"
    PINCH = "pinch"
    LONG_PRESS = "long_press"
    BACK = "back"
    HOME = "home"
    WAIT = "wait"


# WDA UI 元素类型映射
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


# 设备连接状态
class ConnectionState(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN = "unknown"


# 设备平台类型
class PlatformType(Enum):
    IOS = "ios"
    ANDROID = "android"
    SIMULATOR = "simulator"
    OTHER = "other"


# Agent 主循环状态机节点
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


# 验证层级：动作级/状态级/目标级
class ValidationLevel(Enum):
    ACTION = "action"
    STATE = "state"
    GOAL = "goal"


# 错误分类
class ErrorCategory(Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    PAGE_NOT_EXPECTED = "page_not_expected"
    APP_CRASH = "app_crash"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


# 错误严重程度
class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# 恢复策略类型
class RecoveryStrategy(Enum):
    RETRY = "retry"
    SKIP_STEP = "skip"
    REPLAN = "re_decide"
    FALLBACK = "fallback"
    ABORT_TASK = "abort"
    RESTART_APP = "restart_app"
    GO_HOME = "go_home"


@dataclass
# UI 元素的矩形区域（x, y, width, height）
class Rect:
    x: float = 0
    y: float = 0
    width: float = 0
    height: float = 0

    @property
    def center(self) -> Tuple[float, float]:
        return self.x + self.width / 2, self.y + self.height / 2


@dataclass
# WDA 解析后的单个 UI 元素，包含类型、文本、位置、可交互性等属性
class UIElement:
    """
    UI 元素定义。
    
    从 WDA XML 解析出的单个 UI 组件，包含类型、文本、位置、可交互性等属性。
    semantic_text 属性用于生成人类可读的元素描述。
    """
    """
    UI 元素定义。
    
    从 WDA XML 解析出的单个 UI 组件，包含类型、文本、位置、可交互性等属性。
    semantic_text 属性用于生成人类可读的元素描述。
    """
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
# 设备动态状态（连接、电量、前台应用等），每轮观察时更新
class DeviceStatus:
    """
    设备状态。
    
    动态设备状态，如连接状态、电量、网络、前台应用等。
    由 Device.check_status() 返回，每轮观察时更新。
    """
    """
    设备状态。
    
    动态设备状态，如连接状态、电量、网络、前台应用等。
    由 Device.check_status() 返回，每轮观察时更新。
    """
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
# 设备静态信息（平台、分辨率、系统版本等）
class DeviceInfo:
    """
    设备信息。
    
    静态设备属性，如平台类型、屏幕分辨率、系统版本等。
    由 Device.get_info() 返回。
    """
    """
    设备信息。
    
    静态设备属性，如平台类型、屏幕分辨率、系统版本等。
    由 Device.get_info() 返回。
    """
    device_id: str = "unknown"
    platform: PlatformType = PlatformType.IOS
    model: str = "unknown"
    os_version: str = "unknown"
    screen_resolution: Tuple[int, int] = (0, 0)
    pixel_ratio: float = 1.0
    capabilities: Dict[str, Any] = field(default_factory=dict)


@dataclass
# 设备截图和 UI 树的原始数据
class ScreenCapture:
    screenshot_path: str = ""
    ui_tree: List[UIElement] = field(default_factory=list)
    raw_ui_tree: Any = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
# 设备操作的执行结果（成功/失败、消息、耗时）
class OperationResult:
    success: bool
    message: str = ""
    raw_response: Any = None
    duration: float = 0.0


@dataclass
# 两次观察之间的页面变化（新增/移除/修改的元素）
class ObservationDiff:
    """
    页面观察结果。
    
    PerceptionLayer 的输出，包含当前页面名称、UI 元素列表、截图路径、
    设备状态和可用动作。是 Planner 决策的主要输入。
    """
    """
    页面观察结果。
    
    PerceptionLayer 的输出，包含当前页面名称、UI 元素列表、截图路径、
    设备状态和可用动作。是 Planner 决策的主要输入。
    """
    added: List[UIElement] = field(default_factory=list)
    removed: List[UIElement] = field(default_factory=list)
    changed: List[UIElement] = field(default_factory=list)
    page_changed: bool = False
    is_loading: bool = False
    has_alert: bool = False
    has_keyboard: bool = False


@dataclass
# PerceptionLayer 的输出，包含页面名称、UI 元素、截图、设备状态等
class Observation:
    """
    页面观察结果。
    
    PerceptionLayer 的输出，包含当前页面名称、UI 元素列表、截图路径、
    设备状态和可用动作。是 Planner 决策的主要输入。
    """
    """
    页面观察结果。
    
    PerceptionLayer 的输出，包含当前页面名称、UI 元素列表、截图路径、
    设备状态和可用动作。是 Planner 决策的主要输入。
    """
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
# Planner 输出的抽象动作定义（类型、目标、值、元素 ID）
class Action:
    type: ActionType
    target: str = ""
    value: str = ""
    # 执行阶段使用的确定性 UI 元素引用，来自当前 Observation.elements[].id。
    # target 仅作为人类可读日志/兼容旧决策，不再作为主要模糊定位依据。
    element_id: str = ""


@dataclass
# Planner 的完整决策输出，包含动作、理由、验证、进度更新等
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
# Executor 执行动作后的完整记录
class ActionRecord:
    """
    动作执行记录。
    
    Executor 执行动作后的完整记录，包含动作定义、执行结果、耗时和截图。
    用于 Memory 存储、验证和状态报告。
    """
    """
    动作执行记录。
    
    Executor 执行动作后的完整记录，包含动作定义、执行结果、耗时和截图。
    用于 Memory 存储、验证和状态报告。
    """
    action: Action
    device_method: str
    parameters: Dict[str, Any]
    result: OperationResult
    screenshot_after: str = ""
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0



@dataclass
# LLM 对"上一步动作"的验证结果
class LLMValidation:
    """
    LLM 验证上下文。
    
    传递给 LLM 用于验证上一步动作的上下文信息，包含动作详情和当前观察。
    由 AgentLoop 构建，Planner 使用。
    """
    """
    LLM 验证上下文。
    
    传递给 LLM 用于验证上一步动作的上下文信息，包含动作详情和当前观察。
    由 AgentLoop 构建，Planner 使用。
    """
    """LLM 对"上一步动作"的验证结果"""
    passed: bool
    reason: str
    observation_summary: str = ""

@dataclass
# Validator 的验证输出（通过/失败、级别、消息、证据）
class ValidationResult:
    """
    验证结果。
    
    Validator 对动作或目标的验证输出，包含是否通过、验证级别、原因和证据。
    用于更新 TaskProgress 和决定是否需要恢复。
    """
    """
    验证结果。
    
    Validator 对动作或目标的验证输出，包含是否通过、验证级别、原因和证据。
    用于更新 TaskProgress 和决定是否需要恢复。
    """
    passed: bool
    level: ValidationLevel = ValidationLevel.ACTION
    message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
# 单轮执行的完整记录（决策、动作、验证、观察前后）
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
# 任务执行指标（起止时间、动作数、失败数、恢复数）
class TaskMetrics:
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
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
# 任务执行进度（已完成目标、当前焦点、动作计数、置信度）
class TaskProgress:
    """
    任务执行进度跟踪。
    
    记录已完成的目标、当前轮次、累积动作数和置信度。
    每轮执行后由 AgentLoop 更新，用于 Planner 决策和状态报告。
    """
    """
    任务执行进度跟踪。
    
    记录已完成的目标、当前轮次、累积动作数和置信度。
    每轮执行后由 AgentLoop 更新，用于 Planner 决策和状态报告。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    completed_objectives: List[str] = field(default_factory=list)
    pending_hints: List[str] = field(default_factory=list)
    current_focus: str = "初始化"
    action_count: int = 0
    last_decision: Optional[NextDecision] = None
    confidence: float = 0.0


@dataclass
# 任务目标定义（描述、成功标准、约束、最大动作数、超时）
class TaskGoal:
    """
    任务目标定义。
    
    包含任务的描述性目标、可验证的成功标准、执行约束和参数配置。
    success_criteria 用于 Validator 判断任务是否完成。
    """
    """
    任务目标定义。
    
    包含任务的描述性目标、可验证的成功标准、执行约束和参数配置。
    success_criteria 用于 Validator 判断任务是否完成。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    description: str
    success_criteria: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    max_actions: int = 30
    timeout: float = 600.0


@dataclass
# 任务实体，Agent 执行的最小工作单元
class Task:
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
    """
    任务定义。
    
    Agent 执行的最小工作单元，包含目标描述、成功标准、约束条件和执行参数。
    通过 WorkflowEngine 转换为 Workflow 进行实际执行。
    """
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
# Planner 决策时的完整上下文（目标、进度、观察、设备、记忆、状态）
class ExecutionContext:
    task_goal: TaskGoal
    progress: TaskProgress
    observation: Observation
    device_status: DeviceStatus
    device_info: DeviceInfo
    memory: Memory
    state: AgentRunState


@dataclass
# 结构化错误信息（分类、严重程度、消息、建议恢复策略）
class ErrorInfo:
    """
    错误信息。
    
    结构化的错误描述，包含分类、严重程度、消息和上下文。
    用于异常处理和恢复决策。
    """
    """
    错误信息。
    
    结构化的错误描述，包含分类、严重程度、消息和上下文。
    用于异常处理和恢复决策。
    """
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.LOW
    code: str = ""
    message: str = ""
    context: str = ""
    timestamp: float = field(default_factory=time.time)
    suggested_strategy: RecoveryStrategy = RecoveryStrategy.REPLAN


@dataclass
# Agent 运行时状态快照，用于状态报告和调试
class AgentState:
    """
    Agent 运行时状态。
    
    包含任务状态、进度、当前轮次、最后观察和决策、错误信息等。
    用于状态报告和调试。
    """
    """
    Agent 运行时状态。
    
    包含任务状态、进度、当前轮次、最后观察和决策、错误信息等。
    用于状态报告和调试。
    """
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
# Agent 执行统计（成功率、轮次、恢复、截图数、LLM 耗时等）
class AgentStats:
    """
    Agent 执行统计。
    
    记录动作成功率、验证通过率、恢复次数、总轮次等指标。
    用于性能分析和优化。
    """
    """
    Agent 执行统计。
    
    记录动作成功率、验证通过率、恢复次数、总轮次等指标。
    用于性能分析和优化。
    """
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
# 传递给下一轮 LLM 的上一步动作上下文，用于验证
class ActionContext:
    """
    动作上下文。
    
    用于 LLM 验证的简化动作信息，包含类型、目标、预期结果和实际结果。
    在每轮开始时由 AgentLoop 构建。
    """
    """
    动作上下文。
    
    用于 LLM 验证的简化动作信息，包含类型、目标、预期结果和实际结果。
    在每轮开始时由 AgentLoop 构建。
    """
    """上一步动作的上下文，用于 LLM 验证"""
    action_type: str
    action_target: str
    action_value: str
    page_before: str
    expected_outcome: str
    execution_result: str  # "success" | "failed" | "unknown"
