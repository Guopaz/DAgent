# Mobile Agent 架构设计方案

## 一、项目目标

实现一个面向多端设备的移动自动化 Agent，通过统一的 **Device 抽象层** 屏蔽底层平台差异，并通过自然语言驱动完成移动端操作任务。WDA（WebDriverAgent）只是 iOS 设备的一种具体实现，Android、模拟器或其他设备类型可基于同一抽象接口接入。

### 1.1 核心能力

| 能力 | 说明 |
|------|------|
| 自然语言任务输入 | 用户以自然语言描述任务，Agent 自动解析并执行 |
| UI 自动理解 | 自动解析页面结构，识别可交互元素 |
| 页面状态识别 | 感知当前页面状态，判断所处流程阶段 |
| 自动规划执行 | 基于目标与当前状态，自主决策下一步动作 |
| 自动验证结果 | 每次执行后独立验证动作是否成功 |
| 异常恢复 | 遇到异常时自动重试、回退或切换策略 |
| 长任务执行 | 支持多步骤、长时间运行的复杂任务 |

### 1.2 示例场景

> **用户输入：** "打开 Boss 直聘，搜索 iOS 开发，投递前三个岗位"
>
> **Agent 行为：** 自动完成 App 启动 → 登录 → 搜索 → 逐个投递的全流程。

---

## 二、总体架构

### 2.1 分层流水线

整体采用 **分层流水线** 架构：任务从顶层进入，依次经过各模块处理，最终通过 Memory 反馈形成闭环。

```
┌──────────────────────┐
│      User Task       │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    Task Manager      │  ← 任务接收与生命周期管理
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   Workflow Engine    │  ← 管理任务上下文与滚动决策流转
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    State Machine     │  ← 约束当前阶段允许的行为
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Perception Layer    │  ← 通过 Device 感知状态（UI 树 + 截图）
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Planner         │  ← 基于当前状态决策下一步动作
│       (LLM)          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Executor        │  ← 将抽象动作翻译为 Device 操作
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│      Validator       │  ← 独立验证执行结果（三级验证）
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│       Memory         │  ← 上下文记忆与状态追踪
└──────────────────────┘
```

### 2.2 模块间依赖关系

```
Task Manager ──创建──→ Workflow Engine ──初始化──→ State Machine
                                                         │
Perception Layer ←──获取状态──┐                          │
       │                     │                          │
       ▼                     │                          ▼
   Planner ──输出动作──→ Executor ──调用──→ Device
       │                                    │
       ▼                                    ▼
   Validator ──验证结果──→ Memory ──反馈──→ Perception Layer
       │
       ▼
  Recovery Manager ──异常时介入──→ 重新观察 / 重新决策 / 终止
```

**Device 抽象层位置：**

```
Perception Layer ──读取──┐
                         ▼
                    Device (抽象接口)
                         ▲
Executor ────────操作────┘
                         │
            ┌────────────┼────────────┐
            ▼            ▼            ▼
       IOSWDADevice  AndroidDevice  SimulatorDevice ...
```

Perception Layer 和 Executor 只依赖 `Device` 抽象接口，不直接依赖 WDA、ADB 或其他底层协议。新增设备类型时只需要实现对应的 `Device` 子类，不需要修改 Planner / Workflow / Validator 等上层模块。

**关键设计约束：**

| 约束 | 说明 |
|------|------|
| Planner 与 Validator 分离 | Validator 必须独立于 Planner，避免 LLM "自己判自己" |
| Planner 只负责下一步决策 | 不一次性生成完整步骤列表；每轮基于任务目标、历史进度和设备状态决定下一步 |
| 语义化动作 | 所有动作目标使用语义化描述（如 `click("登录")`），不暴露屏幕坐标 |
| 单 Agent 单任务 | 避免状态冲突；多设备并行通过 AgentPool 实现 |
| 上层依赖 Device 抽象 | Perception / Executor 不直接调用 WDA 或 ADB，避免平台耦合 |

### 2.3 数据流概览

> 设计调整：数据流采用 **滚动式决策（Rolling Decision）**。系统不在任务开始时一次性生成全部 `PlanStep` 列表，而是在每一轮循环中根据 **任务目标、已完成进度、当前设备状态、页面观察结果和历史动作** 动态决策下一步该做什么。

```
用户输入 (Task)
    │
    ▼
Task Manager ──→ 创建 Task + AgentState + TaskGoal
    │
    ▼
Workflow Engine ──→ 初始化 ExecutionContext（目标、约束、进度、检查点）
    │
    ▼
┌─── 滚动决策循环（直到任务完成 / 失败 / 中止）──────────────┐
│                                                           │
│  1. Device.check_status() 检查连接、锁屏、前后台等状态      │
│  2. 前置清理（弹窗 / 键盘 / 加载状态）                    │
│  3. Perception → Device.capture_screen() → Observation     │
│  4. State Machine 约束检查                                │
│  5. Workflow Engine 汇总 DecisionContext                  │
│     - 原始任务目标                                        │
│     - 当前任务进度 / 已完成子目标                         │
│     - 当前页面与设备状态                                  │
│     - 历史动作、失败记录、恢复次数                        │
│  6. Planner → NextDecision（下一步动作 / 标记完成 / 恢复） │
│  7. Executor → Device 操作执行                            │
│  8. Validator → 动作、状态、目标进展验证                  │
│  9. Memory + AgentState 更新进度并保存检查点              │
│                                                           │
│  若目标已达成 → 任务完成                                  │
│  若动作失败/状态异常 → Recovery Manager 介入              │
│  若需要继续 → 回到第 1 步重新观察并决策                   │
└───────────────────────────────────────────────────────────┘
    │
    ▼
生成执行报告 → 任务结束
```

**核心变化：**

| 旧设计 | 新设计 |
|--------|--------|
| 启动时生成完整 `Plan.steps: List[PlanStep]` | 启动时只初始化目标、约束和进度上下文 |
| 外层按固定步骤逐个执行 | 每轮根据真实设备状态动态选择下一步 |
| 页面变化后依赖重新规划完整计划 | 页面变化后只重新计算下一步决策 |
| 步骤完成作为主要推进条件 | 任务进度、目标验证和检查点共同驱动推进 |

---

## 三、核心数据模型

> 以下为各模块共用的基础数据结构定义，模块设计章节中直接引用。

### 3.1 任务、进度与决策模型

```python
class Task:
    id: str                        # 任务唯一标识
    goal: str                      # 任务目标（自然语言）
    params: Dict[str, Any]         # 任务参数
    status: TaskStatus             # 任务状态
    priority: TaskPriority         # 优先级
    created_at: datetime           # 创建时间
    updated_at: datetime           # 最后更新时间
    progress: TaskProgress         # 任务进度，而非预生成步骤列表
    results: List[ProgressRecord]  # 每轮决策与执行记录
    metrics: TaskMetrics           # 执行指标

class TaskStatus(Enum):
    CREATED     = "created"        # 已创建，等待启动
    RUNNING     = "running"        # 执行中
    PAUSED      = "paused"         # 已暂停
    COMPLETED   = "completed"      # 目标已达成
    PARTIAL     = "partial"        # 部分目标已达成
    ABORTED     = "aborted"        # 用户主动中止
    FAILED      = "failed"         # 执行失败
    TIMED_OUT   = "timed_out"      # 超时终止

class TaskPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class TaskGoal:
    description: str               # 原始任务目标
    success_criteria: List[str]    # 任务完成判定条件
    constraints: List[str]         # 执行约束，如账号、时间、禁止操作
    max_actions: int               # 最大动作数，防止无限循环
    timeout: float                 # 任务超时时间

class TaskProgress:
    completed_objectives: List[str] # 已确认完成的子目标/里程碑
    pending_hints: List[str]        # 仍需关注的目标提示（非固定步骤）
    current_focus: str              # 当前关注点，如“进入搜索页”“投递第 2 个岗位”
    action_count: int               # 已执行动作数
    last_decision: NextDecision     # 最近一次决策
    confidence: float              # 对任务进展判断的置信度

class ExecutionContext:
    task_goal: TaskGoal             # 任务目标和成功标准
    progress: TaskProgress          # 当前任务进度
    observation: Observation        # 当前页面观察
    device_status: DeviceStatus     # 当前设备状态
    device_info: DeviceInfo         # 设备型号、系统版本、分辨率等信息
    memory: Memory                  # 历史动作、页面路径、失败记录
    state: AgentState               # Agent 运行状态

class DecisionType(Enum):
    ACTION = "action"              # 执行一个下一步动作
    WAIT = "wait"                  # 等待页面/网络/加载完成
    COMPLETE = "complete"          # 任务目标已达成
    RECOVER = "recover"            # 进入恢复流程
    ABORT = "abort"                # 终止任务

class NextDecision:
    type: DecisionType             # 决策类型
    reason: str                    # 决策原因
    action: Optional[Action]       # 当 type=ACTION 时的动作
    expected_outcome: str          # 执行后的预期变化
    progress_update: List[str]     # 本轮可确认的进展
    validation_hint: str           # 给 Validator 的验证提示

class ProgressRecord:
    round_index: int               # 第几轮滚动决策
    focus: str                     # 本轮关注点
    decision: NextDecision         # 本轮决策
    action_record: Optional[ActionRecord]  # 动作执行记录
    validation: ValidationResult   # 验证结果
    observation_before: Observation # 执行前观察
    observation_after: Observation  # 执行后观察
    duration: float                # 耗时（秒）
    error: str                     # 错误信息（如有）
```

> 说明：`pending_hints` 只是辅助 Planner 理解剩余目标的提示，不代表固定、必须顺序执行的 `PlanStep`。真正的下一步由每轮 `ExecutionContext` 动态决定。

### 3.2 Device 抽象模型

`Device` 是 Agent 与真实设备、模拟器或云设备交互的唯一抽象接口。上层模块只能依赖该接口，不能直接依赖 WDA、ADB、Appium 等具体实现。

#### 3.2.1 核心接口

```python
from abc import ABC, abstractmethod

class Device(ABC):
    """移动设备抽象基类。

    任何具体设备实现（iOS WDA、Android ADB、模拟器、云真机）都必须实现以下能力：
    1. 设备状态检查
    2. 屏幕采集
    3. 设备操作
    4. 设备信息获取
    """

    @abstractmethod
    async def check_status(self) -> DeviceStatus:
        """检查设备状态：连接状态、锁屏状态、前后台、网络、电量等。"""

    @abstractmethod
    async def capture_screen(self) -> ScreenCapture:
        """采集当前屏幕信息，至少包含截图和 UI 树。"""

    @abstractmethod
    async def get_info(self) -> DeviceInfo:
        """获取设备型号、系统版本、分辨率等静态或半静态信息。"""

    @abstractmethod
    async def click(self, x: float, y: float) -> OperationResult:
        """点击屏幕坐标。Executor 负责将语义化目标解析为坐标或元素中心点。"""

    @abstractmethod
    async def swipe(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        duration: float = 0.2,
    ) -> OperationResult:
        """滑动屏幕。"""

    @abstractmethod
    async def input_text(self, text: str) -> OperationResult:
        """向当前焦点输入文本。"""

    @abstractmethod
    async def press_back(self) -> OperationResult:
        """返回上一页；iOS 可映射为导航返回或系统手势，Android 可映射为 Back Key。"""

    @abstractmethod
    async def press_home(self) -> OperationResult:
        """回到系统桌面。"""

    @abstractmethod
    async def wait(self, seconds: float) -> OperationResult:
        """等待设备状态稳定。"""
```

#### 3.2.2 Device 相关数据结构

```python
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

class DeviceStatus:
    connection: ConnectionState     # 连接状态
    is_locked: bool                 # 是否锁屏
    foreground_app: str             # 当前前台 App / 包名
    target_app_foreground: bool     # 目标 App 是否在前台
    screen_on: bool                 # 屏幕是否点亮
    network_reachable: bool         # 网络是否可用
    battery_level: float            # 电量，0.0 ~ 1.0
    orientation: str                # portrait / landscape
    healthy: bool                   # 是否可继续执行自动化
    message: str                    # 状态说明或异常原因

class DeviceInfo:
    device_id: str                  # 设备唯一标识
    platform: PlatformType          # 平台类型
    model: str                      # 设备型号，如 iPhone 15 / Pixel 8
    os_version: str                 # 系统版本，如 iOS 17.5 / Android 14
    screen_resolution: Tuple[int, int] # 屏幕分辨率，width x height
    pixel_ratio: float              # 设备像素比
    capabilities: Dict[str, Any]    # 设备能力，如是否支持 UI 树、是否支持多指手势

class ScreenCapture:
    screenshot_path: str            # 截图文件路径
    ui_tree: List[UIElement]        # 标准化后的 UI 树
    raw_ui_tree: Any                # 平台原始 UI 树，便于调试
    timestamp: float                # 采集时间
    metadata: Dict[str, Any]        # 页面标题、Activity、BundleId 等平台元信息

class OperationResult:
    success: bool                   # 操作是否成功下发
    message: str                    # 操作结果描述
    raw_response: Any               # 底层驱动原始响应
    duration: float                 # 操作耗时
```

#### 3.2.3 具体实现示例

| 实现类 | 底层协议/工具 | 说明 |
|--------|---------------|------|
| `IOSWDADevice` | WDA / WebDriverAgent | iOS 真机或模拟器的默认实现 |
| `AndroidDevice` | ADB / uiautomator2 | Android 真机或模拟器实现 |
| `AppiumDevice` | Appium WebDriver | 跨平台实现，适合已有 Appium 基础设施 |
| `MockDevice` | 本地 Mock | 单元测试和离线回放 |

`IOSWDADevice` 只是 `Device` 的一个实现示例：

```python
class IOSWDADevice(Device):
    def __init__(self, wda_client: WDAClient):
        self.client = wda_client

    async def check_status(self) -> DeviceStatus:
        # 通过 WDA status/session/app_state 等接口转换为统一 DeviceStatus
        ...

    async def capture_screen(self) -> ScreenCapture:
        # 截图 + source，转换为统一 UIElement 列表
        ...

    async def click(self, x: float, y: float) -> OperationResult:
        # 映射为 WDA tap
        ...
```

### 3.3 UI 与观察模型

```python
class UIElement:
    id: str                        # 元素唯一标识
    type: ElementType              # 元素类型
    text: str                      # 显示文本
    label: str                     # 无障碍标签
    value: str                     # 当前值
    visible: bool                  # 是否可见
    enabled: bool                  # 是否可用
    clickable: bool                # 是否可点击
    frame: Rect                    # 屏幕位置与尺寸
    attributes: Dict[str, str]     # 附加属性

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

class Observation:
    page_name: str                          # 页面名称
    elements: List[UIElement]               # 标准化后的页面元素列表
    screenshot_path: str                    # 截图文件路径
    raw_ui_tree: Any                        # 平台原始 UI 树
    device_status: DeviceStatus             # 采集时设备状态
    device_info: DeviceInfo                 # 设备信息
    page_metadata: Dict[str, Any]           # 页面元数据（标题、URL、Activity、BundleId 等）
    available_actions: List[str]            # 当前页面可执行的动作
    diff_from_previous: ObservationDiff     # 与上一次观察的差异

class ObservationDiff:
    added: List[UIElement]         # 新增的元素
    removed: List[UIElement]       # 移除的元素
    changed: List[UIElement]       # 属性变化的元素
    page_changed: bool             # 页面是否发生变化
    is_loading: bool               # 页面是否在加载
    has_alert: bool                # 是否有弹窗
    has_keyboard: bool             # 是否有键盘
```

### 3.4 动作模型

```python
class ActionType(Enum):
    CLICK       = "click"          # 点击元素
    INPUT       = "input"          # 输入文本
    SWIPE_UP    = "swipe_up"       # 向上滑动
    SWIPE_DOWN  = "swipe_down"     # 向下滑动
    LONG_PRESS  = "long_press"     # 长按
    BACK        = "back"           # 返回上一页
    HOME        = "home"           # 回到主屏幕
    WAIT        = "wait"           # 等待

class Action:
    type: ActionType               # 动作类型
    target: str                    # 动作目标（语义化描述，非坐标）
    value: str                     # 动作参数（如输入文本）

class ActionRecord:
    action: Action                 # Planner 输出的语义化动作
    device_method: str             # 实际调用的 Device 方法，如 click / swipe / input_text
    parameters: Dict               # Device 调用参数
    result: OperationResult        # Device 操作结果
    screenshot_after: str          # 执行后截图
    timestamp: float               # 执行时间
    duration: float                # 耗时
```

> **设计原则 — 语义化动作：** 所有动作目标使用语义化描述，而非屏幕坐标。

| ❌ 错误设计 | ✅ 正确设计 |
|------------|------------|
| `tap(123, 456)` | `click("登录按钮")` |

### 3.5 错误与恢复模型

```python
class ErrorCategory(Enum):
    ELEMENT_NOT_FOUND = "element_not_found"
    PAGE_NOT_EXPECTED = "page_not_expected"
    APP_CRASH = "app_crash"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"

class ErrorSeverity(Enum):
    LOW = "low"                    # 可自动恢复
    MEDIUM = "medium"              # 需要策略介入
    HIGH = "high"                  # 需要人工干预
    CRITICAL = "critical"          # 任务无法继续

class ErrorInfo:
    category: ErrorCategory        # 错误分类
    severity: ErrorSeverity        # 严重程度
    code: str                      # 错误码
    message: str                   # 错误描述
    context: str                   # 错误上下文
    timestamp: float               # 发生时间
    suggested_strategy: RecoveryStrategy  # 建议恢复策略

class RecoveryStrategy(Enum):
    RETRY = "retry"                # 重试当前动作
    SKIP_STEP = "skip"             # 跳过当前不可达子目标
    REPLAN = "re_decide"           # 重新构建上下文并决策
    FALLBACK = "fallback"          # 降级到备选方案
    ABORT_TASK = "abort"           # 终止任务
    RESTART_APP = "restart_app"    # 重启应用
    GO_HOME = "go_home"            # 回到主屏幕
```

---

## 四、核心模块设计

### 4.1 Task Manager（任务管理器）

**职责：** 接收并管理用户任务的全生命周期。

**输入示例：**

```json
{
    "task": "投递职位",
    "params": {
        "keyword": "iOS开发"
    }
}
```

**核心职责：**

- 创建任务实例并分配优先级
- 生成对应的 Workflow（调用 Workflow Engine）
- 绑定或创建 `Device` 实例，初始化运行上下文（AgentState）
- 管理任务生命周期状态转换
- 持久化快照，支持中断恢复
- 记录执行历史、设备调用指标与任务指标

#### 任务生命周期状态机

```
                    ┌──────────────┐
                    │   CREATED    │  初始状态
                    └──────┬───────┘
                           │ start()
                           ▼
                    ┌──────────────┐
            ┌──────│   RUNNING    │──────┐
            │      └──────┬───────┘      │
            │ pause()     │              │ timeout
            ▼             │              ▼
     ┌──────────┐         │       ┌───────────┐
     │  PAUSED  │─────────┘       │ TIMED_OUT │
     └──────────┘  resume()       └───────────┘
            │
            │ abort()
            ▼
     ┌──────────┐
     │ ABORTED  │
     └──────────┘

     正常结束：
     ┌───────────┐  任务目标全部达成   ┌───────────┐
     │  RUNNING  │───────────────→│ COMPLETED │
     └───────────┘                └───────────┘
     ┌───────────┐  部分任务目标达成   ┌───────────┐
     │  RUNNING  │───────────────→│  PARTIAL  │
     └───────────┘                └───────────┘
     ┌───────────┐  执行异常       ┌───────────┐
     │  RUNNING  │───────────────→│  FAILED   │
     └───────────┘                └───────────┘
```

#### 任务快照（TaskSnapshot）

支持在任意时刻中断并从断点恢复：

```python
class TaskSnapshot:
    task_id: str                   # 任务 ID
    status: TaskStatus             # 中断时的状态
    current_node: str              # 当前 Workflow 节点
    task_goal: TaskGoal            # 任务目标与成功标准
    progress: TaskProgress         # 当前任务进度
    last_observation: Observation  # 最近一次观察
    device_status: DeviceStatus    # 最近一次设备状态
    device_info: DeviceInfo        # 当前设备信息
    records: List[ProgressRecord]  # 历史滚动决策记录
    contexts: dict                 # 其他上下文信息
    timestamp: float               # 快照时间戳
```

**持久化时机：**

| 时机 | 说明 |
|------|------|
| 每轮决策验证完成后 | 自动保存最新观察、进度与历史动作 |
| 确认新的子目标/里程碑后 | 保存任务进展检查点 |
| 状态变更时 | RUNNING → PAUSED / FAILED / TIMED_OUT |
| 异常恢复前 | 保存中断前的完整上下文 |
| 用户主动暂停时 | 立即持久化 |

**存储结构：**

```
snapshots/
├── task_{id}_latest.json          # 最新快照（用于恢复）
├── task_{id}_round_{n}.json       # 每轮滚动决策快照
└── task_{id}_checkpoint.json      # 关键进展检查点快照
```

**恢复流程：** 加载最新快照 → 重建 Task / TaskProgress → 重新绑定 Device → 检查设备状态并重新感知页面 → 基于最新状态继续滚动决策。

---

### 4.2 Workflow Engine（工作流引擎）

**职责：** 管理任务目标、执行上下文、进度检查点和阶段流转，不再负责一次性生成完整 `PlanStep` 序列。

**核心模型：**

```python
class Workflow:
    task_id: str                   # 关联的任务 ID
    goal: TaskGoal                 # 任务目标与成功标准
    progress: TaskProgress         # 当前任务进度
    current_node: str              # 当前工作流节点（observe/decide/execute/validate/recover）
    status: WorkflowStatus         # 工作流状态

    def build_decision_context(
        self,
        observation: Observation,
        device_status: DeviceStatus,
        device_info: DeviceInfo,
        memory: Memory,
    ) -> ExecutionContext:
        """汇总当前任务、页面、设备和历史信息，供 Planner 做下一步决策"""
```

**职责边界：**

| 模块 | 职责 |
|------|------|
| **Workflow Engine** | 维护目标、约束、进度、检查点，组织滚动决策循环 |
| **Planner** | 基于 `ExecutionContext` 决定下一步动作或状态（ACTION / WAIT / COMPLETE / RECOVER / ABORT） |
| **Validator** | 独立判断动作是否成功、页面状态是否符合预期、任务目标是否取得新进展 |

**示例：** 任务“搜索 iOS 开发并投递前三个岗位”

启动时不生成固定步骤列表，只初始化目标与成功标准：

```python
TaskGoal(
    description="打开 Boss 直聘，搜索 iOS 开发，投递前三个岗位",
    success_criteria=[
        "已进入 Boss 直聘",
        "搜索关键词为 iOS 开发",
        "已成功投递 3 个不同岗位",
    ],
    constraints=["遇到登录或权限弹窗时优先处理", "不要重复投递同一岗位"],
)
```

执行过程中每轮动态决策：

```
Round 1: 观察到设备在桌面 → 决策：打开 Boss 直聘
Round 2: 观察到首页有搜索入口 → 决策：点击搜索框
Round 3: 观察到搜索输入框激活 → 决策：输入“iOS开发”
Round 4: 观察到职位列表 → 决策：打开第一个未投递职位
Round N: Validator 确认已投递 3 个岗位 → 决策：COMPLETE
```

**流转规则：**

| 当前决策/验证结果 | 下一步行为 |
|------------------|-----------|
| ACTION 且验证通过 | 更新进度与 Memory，重新观察并继续决策 |
| WAIT | 等待后重新观察 |
| COMPLETE 且目标验证通过 | 标记任务完成 |
| RECOVER 或验证失败 | 进入异常恢复流程 |
| ABORT | 终止任务并生成报告 |

---

### 4.3 State Machine（状态机）

**职责：** 约束 Agent 在每个阶段允许的行为，防止不合理的状态转换。

**核心状态转换：**

```
INIT → OBSERVING → PLANNING → EXECUTING → VALIDATING → OBSERVING (循环)
                                                         │
                                               进展更新 → PROGRESS_UPDATED
                                               任务完成 → TASK_COMPLETED
                                               异常     → RECOVERING → OBSERVING
```

**作用：** 防止 Agent 在未观察状态下直接执行动作，或在未验证状态下跳过检查。状态机确保每个循环阶段按序执行，不允许跳跃。

---

### 4.4 Device Layer（设备抽象层）

**职责：** 提供统一的设备访问接口，屏蔽 iOS / Android / 模拟器 / 云真机等底层差异。

**核心原则：**

| 原则 | 说明 |
|------|------|
| 上层只依赖抽象 | Perception / Executor / Validator 只依赖 `Device`，不依赖 WDA / ADB |
| 平台能力标准化 | 截图、UI 树、设备状态、设备信息统一转换为标准数据模型 |
| 操作语义分层 | Planner 输出语义化动作，Executor 定位元素，Device 只执行坐标/文本/系统键等底层操作 |
| 能力可扩展 | 新设备类型通过实现 `Device` 接口接入，不改上层业务逻辑 |

**接口分组：**

| 能力组 | 方法 | 说明 |
|--------|------|------|
| 设备状态检查 | `check_status()` | 检查连接状态、锁屏、前台 App、网络、电量、屏幕方向等 |
| 屏幕采集 | `capture_screen()` | 返回截图、标准化 UI 树、原始 UI 树和页面元信息 |
| 设备操作 | `click()` / `swipe()` / `input_text()` / `press_back()` / `press_home()` / `wait()` | 执行具体设备操作 |
| 设备信息获取 | `get_info()` | 获取设备型号、系统版本、分辨率、像素比和能力集 |

**实现约束：**

1. `Device` 实现必须把平台元素转换为统一 `UIElement`。
2. `Device` 实现必须保留 `raw_ui_tree` / `raw_response`，用于调试和平台特定问题定位。
3. `click()` / `swipe()` 接收坐标是底层接口设计；上层仍保持语义化动作，由 Executor 负责语义目标定位。
4. 当平台不支持某能力时，需要在 `DeviceInfo.capabilities` 中声明，并在方法返回明确错误，不允许静默失败。

**iOS WDA 实现映射：**

| Device 方法 | WDA 映射 |
|-------------|----------|
| `check_status()` | WDA `/status`、session 状态、前台 App 状态 |
| `capture_screen()` | WDA screenshot + source |
| `click(x, y)` | WDA tap |
| `swipe(...)` | WDA drag / swipe |
| `input_text(text)` | WDA sendKeys / keyboard input |
| `press_home()` | WDA home |
| `get_info()` | WDA device info + session capabilities |

---

### 4.5 Perception Layer（感知层）

**职责：** 从设备获取当前页面状态，提供结构化的观察数据。

**组成：**

| 组件 | 职责 |
|------|------|
| **UI Parser** | 解析 `Device.capture_screen()` 返回的标准化 UI 树；必要时读取平台原始 UI 树 |
| **Screenshot** | 采集设备截图 |
| **Visual Analyzer** | 基于截图进行视觉分析（LLM 辅助，UI 树不可用时降级使用） |
| **Change Detector** | 计算两次观察之间的差异（ObservationDiff） |

**观察策略：**

1. **优先使用 UI 树** — 结构化信息，解析速度快，精确度高
2. **截图作为补充** — 当 UI 树信息不足时，通过视觉模型分析
3. **变化检测** — 每次观察时计算与上一次的差异，识别弹窗、键盘、加载状态

**变化检测算法：**

```python
class ChangeDetector:
    """检测两次观察之间的变化"""

    def detect_changes(self, current: Observation) -> ObservationDiff:
        """
        对比当前观察与上次观察，返回差异信息：
        - 新增 / 移除 / 变化的元素
        - 页面是否整体变化
        - 是否存在弹窗、键盘、加载状态
        """

    def _detect_loading(self, obs: Observation) -> bool:
        """通过关键词检测加载状态：'loading'、'加载中'、'请稍候'等"""

    def _has_alert(self, obs: Observation) -> bool:
        """检测元素列表中是否存在 ALERT 类型"""

    def _has_keyboard(self, obs: Observation) -> bool:
        """检测元素列表中是否存在 KEYBOARD 类型"""
```

**感知流程：** `Device.check_status()` → `Device.get_info()` → `Device.capture_screen()` → 标准化 Observation → 计算 ObservationDiff → 输出 Observation

---

### 4.6 Planner（规划器）

**职责：** 基于 `ExecutionContext` 做出 **滚动式局部决策**，决定当前这一轮下一步应该做什么。

> ⚠️ **关键约束：** Planner 只输出 `NextDecision`，不输出完整 `PlanStep` 列表；每次决策必须显式依赖当前任务进度、页面观察结果和设备状态。

**输入：**

| 参数 | 说明 |
|------|------|
| TaskGoal | 原始任务目标、成功标准、执行约束 |
| TaskProgress | 已完成目标、当前关注点、历史决策摘要 |
| CurrentState | 当前状态机状态 |
| DeviceStatus / DeviceInfo | 连接状态、锁屏、App 前后台、网络、设备型号、系统版本、分辨率等 |
| PageContext | 当前页面上下文（Observation + ObservationDiff） |
| Memory | 历史动作、失败记录、恢复记录、已访问页面 |

**输出：**

```json
{
  "type": "ACTION",
  "reason": "任务需要搜索 iOS 开发，当前已在搜索页面且搜索框可见，下一步应输入关键词",
  "action": {
    "type": "INPUT",
    "target": "搜索框",
    "value": "iOS开发"
  },
  "expected_outcome": "搜索框中出现 iOS开发，随后可触发搜索或展示结果",
  "progress_update": ["已进入搜索页面"],
  "validation_hint": "验证搜索框 value 是否包含 iOS开发，或页面是否出现相关搜索结果"
}
```

Planner 也可以输出非动作决策：

| 决策类型 | 场景 |
|----------|------|
| `WAIT` | 页面加载中、网络暂不可用、动画未结束 |
| `COMPLETE` | 当前观察和历史记录已满足 `success_criteria` |
| `RECOVER` | 当前页面与目标明显偏离，或连续动作无效果 |
| `ABORT` | 设备不可用、权限无法处理、达到安全限制 |

**决策原则：**

1. 优先处理设备和页面干扰因素（锁屏、弹窗、键盘、加载、网络异常）。
2. 只选择一个下一步动作，且动作目标必须可由当前观察或视觉分析支持。
3. 如果当前状态已经满足任务成功标准，输出 `COMPLETE`，不要继续执行无意义动作。
4. 如果信息不足，优先 `WAIT` 或请求重新观察，不要臆造后续步骤。
5. 对重复失败的路径降低优先级，结合 Memory 选择替代动作。

**推荐模型：** GPT-4o Vision / Claude Sonnet

---

### 4.7 Executor（执行器）

**职责：** 将 Planner 输出的语义化抽象动作翻译为 `Device` 操作并执行。

**执行流程：** Action → 定位目标元素（通过 UI 树匹配语义描述）→ 调用 `Device` 抽象接口 → 等待设备响应 → 返回 ActionRecord

---

### 4.8 Validator（验证器）

**职责：** 独立验证每个动作、页面状态和任务进展。

> ⚠️ **关键约束：** Validator **必须独立于 Planner**，不要让 LLM 同时承担决策和验证职责，避免"自己判自己"的问题。

**三级验证体系：**

```
┌─────────────────────────────────────────────────────────────┐
│  Level 1: 动作验证 (Action Validation)                       │
│  验证：动作是否成功执行                                       │
│  时机：execute() 后立即验证                                  │
│  示例：点击"登录" → 检查是否触发了点击事件                    │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  Level 2: 状态验证 (State Validation)                        │
│  验证：页面状态是否符合预期                                   │
│  时机：动作执行后，下一轮 observe() 前                        │
│  示例：点击"登录" → 检查是否跳转到登录页                     │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│  Level 3: 目标验证 (Goal Validation)                         │
│  验证：任务目标或子目标是否达成                                       │
│  时机：每轮验证任务进度，或 Planner 输出 COMPLETE 时最终验证  │
│  示例：任务要求登录 → 检查是否成功登录并进入首页              │
└─────────────────────────────────────────────────────────────┘
```

**验证规则模型：**

```python
class ValidationRule:
    level: ValidationLevel         # 验证级别（ACTION / STATE / GOAL）
    description: str               # 规则描述
    condition: Callable            # 验证条件
    timeout: float                 # 超时时间（秒）
    on_failure: RecoveryStrategy   # 失败时的恢复策略

class ValidationResult:
    passed: bool                   # 是否通过
    level: ValidationLevel         # 验证级别
    message: str                   # 验证消息
    evidence: Dict[str, Any]       # 验证证据（截图、元素等）
    timestamp: float               # 验证时间
```

**验证流程：**

```
执行动作 → Level 1 验证
              │
         ┌────┴────┐
         ↓         ↓
       ✅ 通过    ❌ 失败 → 进入异常恢复
         │
    Level 2 验证
         │
    ┌────┴────┐
    ↓         ↓
  ✅ 通过    ❌ 失败 → 进入异常恢复
    │
  (进度更新或 COMPLETE 时)
    │
 Level 3 验证
    │
┌───┴───┐
↓       ↓
✅ 通过  ❌ 失败 → 进入异常恢复
```

---

### 4.9 Memory（记忆系统）

**职责：** 维护 Agent 运行过程中的上下文信息，支撑决策和恢复。

| 记忆类型 | 内容 | 生命周期 |
|----------|------|----------|
| **短期记忆** | 当前页面、历史动作、失败次数、页面访问路径 | 单次任务内有效 |
| **长期记忆** | 页面特征、历史成功路径、账号信息 | 跨任务持久化 |

**核心模型：**

```python
class Memory:
    task_history: list             # 任务执行历史
    page_history: list             # 页面访问历史
    action_history: list           # 动作执行历史
```

---

### 4.10 Recovery Manager（异常恢复管理器）

**职责：** 根据错误类型和上下文，选择最优恢复策略。

#### 异常分类与恢复策略

| 异常类型 | 恢复策略 | 说明 |
|----------|----------|------|
| **页面未找到** | 重新识别 → 重新截图 → 重新决策 | 逐步降级，从轻量到重量 |
| **元素不存在** | 滚动查找 → 重试 → 视觉识别 | 先尝试在当前页面找到元素 |
| **页面卡死** | Back → Home → 重启 App | 逐步升级干预力度 |
| **网络异常** | 等待 → 刷新 → 重试 | 等待恢复后重新操作 |

#### 恢复策略选择流程

```
错误发生 → 分类 (ErrorCategory)
         → 评估严重度 (ErrorSeverity)
         → 查询历史恢复记录
         → 选择策略：
              ├── LOW 严重度 → 自动重试（最多 3 次）
              ├── MEDIUM 严重度 → LLM 分析后选择策略
              ├── HIGH 严重度 → 切换策略或重新决策
              └── CRITICAL 严重度 → 终止任务
```

#### LLM 辅助恢复

对于 MEDIUM 及以上严重度的错误，使用 LLM 分析最佳恢复策略：

```
输入：错误信息 + 当前页面 + 已尝试恢复次数
输出：{"strategy": "re_decide", "reason": "当前页面与预期不符，建议重新构建上下文并决策下一步"}
```

#### 恢复限制

| 限制项 | 阈值 | 说明 |
|--------|------|------|
| 单轮同类动作最大重试次数 | 3 | 防止无限重试 |
| 单任务最大恢复次数 | 5 | 超出后终止任务 |
| 连续恢复失败阈值 | 5 | 可能卡死，建议人工介入 |

---

## 五、Agent 主循环

### 5.1 设计理念

Agent 的核心运行逻辑遵循 **Observe → Decide → Execute → Validate → Update Progress** 循环。每轮循环都先重新获取设备与页面状态，再基于任务目标和历史进度动态决策下一步，而不是按照预生成步骤列表推进。

### 5.2 完整流程

```
任务启动
  │
  ▼
init: 初始化 TaskGoal / TaskProgress / AgentState
  │
  ▼
refresh: 获取设备状态 + 刷新屏幕状态
  │
  ▼
┌─── rolling loop: 滚动式决策循环 ─────────────────────────────┐
│                                                             │
│  pre_check: 前置检测                                        │
│    ├── 有弹窗 → 自动处理弹窗 → refresh                      │
│    ├── 有键盘 → 自动关闭键盘 → refresh                      │
│    ├── 加载中 → wait → refresh                              │
│    └── 正常 → build_context                                 │
│                                                             │
│  build_context: 汇总 TaskGoal + TaskProgress + Observation  │
│                 + DeviceStatus / DeviceInfo + Memory                      │
│                                                             │
│  decide: Planner 输出 NextDecision                          │
│    ├── ACTION   → execute → validate                        │
│    ├── WAIT     → wait → refresh                            │
│    ├── COMPLETE → final_validate → summary                  │
│    ├── RECOVER  → recovery                                  │
│    └── ABORT    → summary                                   │
│                                                             │
│  validate: 三级验证                                          │
│    ├── passed → update_progress → checkpoint → refresh      │
│    └── failed → recovery                                    │
│                                                             │
│  recovery: 恢复分析                                          │
│    ├── retry       → refresh                                │
│    ├── re_decide   → build_context                          │
│    ├── fallback    → execute fallback → validate            │
│    └── abort       → summary                                │
└─────────────────────────────────────────────────────────────┘
  │
  ▼
summary: 生成执行报告 → 任务结束
```

### 5.3 前置检查机制

在每轮“决策-执行”前，自动检测并处理干扰因素：

| 检测项 | 处理方式 | 后续动作 |
|--------|----------|----------|
| 弹窗 (Alert) | 查找关闭按钮（“关闭”、“取消”、“知道了”等）自动关闭 | 重新观察 |
| 键盘 (Keyboard) | 点击空白区域收起键盘，或根据当前输入任务保留键盘 | 重新观察 / 继续决策 |
| 加载状态 (Loading) | 等待加载完成（关键词检测：“加载中”、“请稍候”等） | 重新观察 |
| App 不在前台 | 拉起目标 App 或回到指定页面 | 重新观察 |
| 网络异常 | 等待、刷新或进入恢复流程 | 重新观察 / 恢复流程 |
| 无法处理 | 返回 ABORT，进入异常恢复 | 恢复流程 |

**前置检查结果：**

| 结果 | 含义 |
|------|------|
| `NORMAL` | 正常，继续构建决策上下文 |
| `HANDLED` | 已处理干扰因素，重新观察 |
| `WAIT` | 需要等待（加载中、网络抖动等），延迟后重新观察 |
| `ABORT` | 无法处理，进入异常恢复 |

### 5.4 单轮滚动决策逻辑

每一轮决策都是一个完整闭环：

```
单轮执行：
  1. 调用 `Device.check_status()` 采集设备状态
  2. 前置清理（弹窗 / 键盘 / 加载 / App 前后台）
  3. 观察（获取 Observation + ObservationDiff）
  4. Workflow Engine 构建 ExecutionContext
  5. Planner 输出 NextDecision
     - ACTION → 执行一个动作
     - WAIT → 等待后重新观察
     - COMPLETE → 进入最终目标验证
     - RECOVER → 进入恢复流程
     - ABORT → 终止任务
  6. Executor 执行动作（仅 ACTION）
  7. Validator 进行三级验证
     - 动作验证：动作是否生效
     - 状态验证：页面/设备状态是否符合预期
     - 目标验证：是否产生新的任务进展，或是否已达成整体目标
  8. Memory + TaskProgress 更新
  9. 保存检查点
 10. 限制检查（最大动作数、最大恢复次数、超时）
```

**终止条件：**

| 条件 | 任务状态 |
|------|----------|
| `success_criteria` 全部通过验证 | COMPLETED |
| 只完成部分可选目标且达到任务边界 | PARTIAL |
| 用户主动中止 | ABORTED |
| 达到超时或最大动作数 | TIMED_OUT / FAILED |
| 恢复失败或遇到不可处理异常 | FAILED |

---

## 六、并发与异步设计

### 6.1 异步架构

Agent 主循环采用异步设计，在等待设备响应和 LLM 响应时让出控制权：

| 操作 | 异步方式 | 说明 |
|------|----------|------|
| 观察 (observe) | `await` | 等待 Device 返回截图、UI 树和设备状态 |
| 决策 (decide) | `await` | 等待 LLM 响应 |
| 执行 (execute) | `await` | 等待 Device 操作执行完成 |
| 验证 (validate) | `await` | 等待页面变化确认 |

### 6.2 并发约束

| 维度 | 约束 | 原因 |
|------|------|------|
| **任务级** | 单 Agent 单任务 | 避免状态冲突，简化调试 |
| **决策轮次级** | 串行执行 | 每轮依赖上一轮观察、验证和进度更新 |
| **动作级** | 串行执行 | 单设备同一时刻只允许一个操作，避免状态竞争 |
| **观察级** | 可异步 | 等待设备响应时可让出控制权 |
| **LLM 调用** | 可异步 | 等待 LLM 响应时可让出控制权 |

### 6.3 资源隔离

每个 Task 分配独立的资源目录，并记录绑定的 Device，防止并发执行时的资源冲突：

```
task_{id}/
├── device.json        # 绑定设备信息（DeviceInfo / capabilities）
├── snapshots/         # 快照目录
├── logs/              # 日志目录
└── screenshots/       # 截图目录
```

### 6.4 多设备并行（可选扩展）

如需支持多设备并行，可通过 AgentPool 管理多个 Agent 实例：

```
AgentPool
├── Agent 1 (Device 1)
├── Agent 2 (Device 2)
└── ...
    └── 共享任务队列（asyncio.Queue）
```

每个 Agent 独立消费任务队列中的任务，并独占一个 `Device` 实例；同一设备不允许被多个 Agent 同时操作。

---

## 七、Agent 状态管理

### 7.1 AgentState 结构

```python
class AgentState:
    task_id: str                           # 当前任务 ID
    task_status: TaskStatus                # 任务状态
    task_goal: TaskGoal                    # 任务目标与成功标准
    progress: TaskProgress                 # 当前任务进度
    current_round: int                     # 当前滚动决策轮次
    current_node: str                      # 当前工作流节点
    last_observation: Observation          # 最近一次观察结果
    device_status: DeviceStatus            # 最近一次设备状态
    device_info: DeviceInfo                # 当前设备信息
    last_decision: NextDecision            # 最近一次下一步决策
    last_error: ErrorInfo                  # 最近一次错误
    total_recoveries: int                  # 总恢复次数
    consecutive_recoveries: int            # 连续恢复次数
    started_at: float                      # 任务开始时间
    last_active_at: float                  # 最后活跃时间
```

### 7.2 执行统计（AgentStats）

```python
class AgentStats:
    total_actions: int = 0                 # 总动作数
    successful_actions: int = 0            # 成功动作数
    failed_actions: int = 0                # 失败动作数
    completed_objectives: int = 0          # 已完成子目标数
    decision_rounds: int = 0               # 滚动决策轮次
    failed_rounds: int = 0                 # 失败轮次数
    recovery_attempts: int = 0             # 恢复尝试次数
    recovery_success_rate: float = 1.0     # 恢复成功率
    screenshot_count: int = 0              # 截图次数
    llm_call_duration: float = 0.0         # LLM 调用总耗时
    llm_token_usage: int = 0               # LLM Token 总用量
    device_call_duration: float = 0.0      # Device 调用总耗时
```

### 7.3 健康监控

通过 StateMonitor 实时检测 Agent 运行健康状态：

| 检查项 | 阈值 | 诊断 |
|--------|------|------|
| 连续恢复次数 | ≥ 5 | 可能卡死，建议终止任务或重启应用 |
| 任务运行时长 | > 30 分钟 | 运行时间过长，建议检查执行状态 |
| 恢复成功率 | < 50%（且恢复次数 > 5） | 恢复策略效果差，建议重新决策或终止 |
| 空闲时间 | > 1 分钟无活动 | 可能卡死，建议检查 Agent 状态 |

---

## 八、Prompt 设计

### 8.1 系统 Prompt 模板

```text
你是一个移动设备自动化 Agent。你的职责是基于当前真实设备状态、设备平台能力和任务进度，决定“下一步”该做什么。
不要生成完整步骤列表，不要假设未来页面一定如何变化。

## 任务目标
{task_goal}

## 成功标准
{success_criteria}

## 当前进度
- 已完成目标: {completed_objectives}
- 当前关注点: {current_focus}
- 已执行动作数: {action_count}
- 最近失败: {recent_failures}

## 设备状态
- 连接状态: {connection}
- 当前 App: {foreground_app}
- 目标 App 是否前台: {target_app_foreground}
- 网络可用: {network_reachable}
- 是否锁屏: {is_locked}
- 屏幕方向: {orientation}
- 设备型号: {device_model}
- 系统版本: {os_version}
- 分辨率: {screen_resolution}

## 当前页面
- 页面名称: {page_name}
- 可交互元素: {elements_list}
- 页面元数据: {metadata}
- 页面变化: {observation_diff}

## 历史动作
{action_history}

## 规则
1. 只能决策一个下一步，不允许输出完整 PlanStep 列表。
2. 决策必须基于当前页面、设备状态和任务进度。
3. 优先使用 UI Tree 信息；UI Tree 不足时参考 Screenshot。
4. 如果页面加载、网络抖动或信息不足，返回 WAIT。
5. 如果当前状态已经满足成功标准，返回 COMPLETE。
6. 如果连续失败或页面偏离目标，返回 RECOVER。
7. 动作目标必须使用语义化描述，不允许使用屏幕坐标。

## 输出格式
{
  "type": "ACTION | WAIT | COMPLETE | RECOVER | ABORT",
  "reason": "决策理由",
  "action": {
    "type": "CLICK | INPUT | SWIPE_UP | SWIPE_DOWN | BACK | HOME | WAIT",
    "target": "语义化目标，如 搜索框 / 登录按钮",
    "value": "可选，输入文本等"
  },
  "expected_outcome": "执行后的预期页面或状态变化",
  "progress_update": ["本轮可确认的进展"],
  "validation_hint": "建议验证器检查的证据"
}
```

---

## 九、目录结构

```
agent/
├── task/                    # 任务管理
│   ├── task.py              #   任务模型定义
│   └── task_manager.py      #   任务管理器
├── workflow/                # 工作流引擎
│   ├── workflow.py          #   工作流模型
│   └── workflow_engine.py   #   工作流引擎
├── state/                   # 状态机
│   ├── state.py             #   状态模型
│   └── state_machine.py     #   状态机管理
├── planner/                 # 规划器
│   ├── planner.py           #   规划逻辑
│   └── prompt.py            #   Prompt 模板
├── perception/              # 感知层
│   ├── ui_parser.py         #   UI 树解析
│   ├── screenshot.py        #   截图采集
│   └── visual_analyzer.py   #   视觉分析
├── executor/                # 执行器
│   ├── executor.py          #   动作执行
│   └── action.py            #   动作模型
├── validator/               # 验证器
│   ├── validator.py         #   结果验证
│   └── rules.py             #   验证规则
├── memory/                  # 记忆系统
│   └── memory.py            #   上下文管理
├── recovery/                # 异常恢复
│   ├── recovery_manager.py  #   恢复管理器
│   └── strategies.py        #   恢复策略
├── monitoring/              # 状态监控
│   ├── state_manager.py     #   Agent 状态管理
│   └── health_monitor.py    #   健康监控
├── device/                  # 设备抽象层
│   ├── base.py              #   Device 抽象基类与数据模型
│   ├── ios_wda.py           #   基于 WDA 的 iOS Device 实现
│   ├── android.py           #   Android Device 实现（如 ADB/uiautomator2）
│   └── mock.py              #   Mock Device，用于测试
└── main.py                  # 入口文件
```

---

## 附录 A：核心数据模型完整字段参考

### A.1 UIElement 完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 元素唯一标识 |
| `type` | `ElementType` | 元素类型（枚举见 3.3 节） |
| `text` | `str` | 显示文本 |
| `label` | `str` | 无障碍标签 |
| `value` | `str` | 当前值 |
| `visible` | `bool` | 是否可见 |
| `enabled` | `bool` | 是否可用 |
| `clickable` | `bool` | 是否可点击 |
| `frame` | `Rect` | 屏幕位置与尺寸 |
| `attributes` | `Dict[str, str]` | 附加属性 |

### A.2 ObservationDiff 计算逻辑

- **元素对比：** 以 `id` 为键，对比两次观察中的元素集合，分为新增（added）、移除（removed）、变化（changed）三类
- **变化判定：** 单个元素的 `text`、`value`、`visible`、`enabled`、`frame` 任一属性不同即视为变化
- **加载检测：** 遍历元素文本，匹配关键词（`loading`、`加载中`、`请稍候`、`progress`）
- **弹窗检测：** 检查元素列表中是否存在 `ElementType.ALERT` 类型
- **键盘检测：** 检查元素列表中是否存在 `ElementType.KEYBOARD` 类型
- **相似度计算：** 基于变化元素数量与总元素数量的比值，范围 0.0 ~ 1.0

### A.3 状态转换规则汇总

| 源状态 | 目标状态 | 触发条件 |
|--------|----------|----------|
| `CREATED` | `RUNNING` | `start()` |
| `RUNNING` | `PAUSED` | `pause()` |
| `PAUSED` | `RUNNING` | `resume()` |
| `RUNNING` | `COMPLETED` | 任务目标全部达成 |
| `RUNNING` | `PARTIAL` | 部分任务目标达成 |
| `RUNNING` | `FAILED` | 执行异常且无法恢复 |
| `RUNNING` | `ABORTED` | 用户主动中止 |
| `RUNNING` | `TIMED_OUT` | 超过超时时间 |

---

## 附录 B：实现参考

> 以下为各模块的关键实现逻辑参考，具体实现细节以代码为准。完整实现代码参见 `架构图.md` 中的类图和流程图。

### B.1 AgentState 管理接口

```python
class StateManager:
    """管理 AgentState 和 AgentStats 的核心接口"""

    def record_action(self, action_record: ActionRecord):
        """记录动作执行结果，更新统计信息"""

    def record_error(self, error: ErrorInfo):
        """记录错误，更新恢复计数"""

    def record_recovery_success(self):
        """记录恢复成功，更新恢复成功率"""

    def record_llm_call(self, duration: float, token_usage: int):
        """记录 LLM 调用的耗时和 Token 用量"""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于日志和监控"""
```

### B.2 状态报告模板

```
=== Agent 状态报告 ===

任务 ID: {task_id}
任务状态: {task_status}
当前轮次: {current_round}
当前关注点: {current_focus}
已完成目标: {completed_objectives}

执行统计:
  - 总动作: {total_actions}  (成功: {successful} / 失败: {failed})
  - 成功率: {success_rate}

恢复统计:
  - 总恢复次数: {total_recoveries}
  - 连续恢复: {consecutive_recoveries}
  - 恢复成功率: {recovery_success_rate}

时间统计:
  - 运行时长: {uptime}s
  - LLM 调用耗时: {llm_duration}s
  - Device 调用耗时: {device_duration}s

资源使用:
  - 截图次数: {screenshot_count}
  - LLM Token: {llm_token_usage}
```
