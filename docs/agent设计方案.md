# Mobile Agent (WDA) 架构设计方案

## 一、项目目标

实现一个基于 **WDA（WebDriverAgent）** 的 iOS 自动化 Agent，通过自然语言驱动完成移动端操作任务。

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
│   Workflow Engine    │  ← 将目标分解为有序步骤
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│    State Machine     │  ← 约束当前阶段允许的行为
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Perception Layer    │  ← 感知设备状态（UI 树 + 截图）
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
│      Executor        │  ← 将抽象动作翻译为 WDA 命令
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
   Planner ──输出动作──→ Executor ──调用──→ WDA Client
       │                                    │
       ▼                                    ▼
   Validator ──验证结果──→ Memory ──反馈──→ Perception Layer
       │
       ▼
  Recovery Manager ──异常时介入──→ 重新观察 / 重新规划 / 终止
```

**关键设计约束：**

| 约束 | 说明 |
|------|------|
| Planner 与 Validator 分离 | Validator 必须独立于 Planner，避免 LLM "自己判自己" |
| Planner 只负责单步决策 | 长链路由 Workflow Engine 控制，Planner 只决定"下一步做什么" |
| 语义化动作 | 所有动作目标使用语义化描述（如 `click("登录")`），不暴露屏幕坐标 |
| 单 Agent 单任务 | 避免状态冲突；多设备并行通过 AgentPool 实现 |

### 2.3 数据流概览

```
用户输入 (Task)
    │
    ▼
Task Manager ──→ 创建 Task + AgentState
    │
    ▼
Workflow Engine ──→ 生成 Plan（有序 PlanStep 列表）
    │
    ▼
┌─── 步骤循环（逐个 PlanStep 执行）────────────────────────┐
│                                                           │
│  ┌── 动作循环（单步骤内多次动作）──────────────────────┐  │
│  │                                                     │  │
│  │  1. 前置清理（弹窗 / 键盘 / 加载状态）              │  │
│  │  2. Perception → Observation + ObservationDiff      │  │
│  │  3. State Machine 约束检查                          │  │
│  │  4. Planner → Action                                │  │
│  │  5. Executor → WDA 命令执行                         │  │
│  │  6. Validator → 三级验证                            │  │
│  │  7. Memory 更新                                     │  │
│  │                                                     │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  步骤完成 → 保存检查点 → 进入下一步骤                     │
│  步骤失败 → Recovery Manager 介入                         │
│                                                           │
└───────────────────────────────────────────────────────────┘
    │
    ▼
生成执行报告 → 任务结束
```

---

## 三、核心数据模型

> 以下为各模块共用的基础数据结构定义，模块设计章节中直接引用。

### 3.1 任务与计划模型

```python
class Task:
    id: str                        # 任务唯一标识
    goal: str                      # 任务目标（自然语言）
    params: Dict[str, Any]         # 任务参数
    status: TaskStatus             # 任务状态
    priority: TaskPriority         # 优先级
    created_at: datetime           # 创建时间
    updated_at: datetime           # 最后更新时间
    results: List[StepResult]      # 步骤执行结果
    metrics: TaskMetrics           # 执行指标

class TaskStatus(Enum):
    CREATED     = "created"        # 已创建，等待启动
    RUNNING     = "running"        # 执行中
    PAUSED      = "paused"         # 已暂停
    COMPLETED   = "completed"      # 全部步骤成功
    PARTIAL     = "partial"        # 部分步骤成功
    ABORTED     = "aborted"        # 用户主动中止
    FAILED      = "failed"         # 执行失败
    TIMED_OUT   = "timed_out"      # 超时终止

class TaskPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"

class Plan:
    goal: str                      # 计划目标
    steps: List[PlanStep]          # 有序步骤列表
    total_steps: int               # 总步骤数

class PlanStep:
    index: int                     # 步骤序号
    description: str               # 步骤描述
    tools_hint: List[str]         # 推荐使用的工具/动作
    result: StepResult             # 执行结果

class StepResult:
    step_index: int                # 对应步骤序号
    description: str               # 步骤描述
    status: StepStatus             # 步骤状态
    actions: List[ActionRecord]    # 动作执行记录
    duration: float                # 耗时（秒）
    error: str                     # 错误信息（如有）

class StepStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    SUCCESS     = "success"
    FAILED      = "failed"
    SKIPPED     = "skipped"
```

### 3.2 UI 与观察模型

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
    elements: List[UIElement]               # 页面元素列表
    screenshot_path: str                    # 截图文件路径
    page_metadata: Dict[str, Any]           # 页面元数据（标题、URL 等）
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

### 3.3 动作模型

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
    tool_name: str                 # 工具/动作名称
    parameters: Dict               # 执行参数
    result: ToolResponse           # 执行结果
    screenshot_after: str          # 执行后截图
    timestamp: float               # 执行时间
    duration: float                # 耗时
```

> **设计原则 — 语义化动作：** 所有动作目标使用语义化描述，而非屏幕坐标。

| ❌ 错误设计 | ✅ 正确设计 |
|------------|------------|
| `tap(123, 456)` | `click("登录按钮")` |

### 3.4 错误与恢复模型

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
    SKIP_STEP = "skip"             # 跳过当前步骤
    REPLAN = "replan"              # 重新规划
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
- 初始化运行上下文（AgentState）
- 管理任务生命周期状态转换
- 持久化快照，支持中断恢复
- 记录执行历史与指标

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
     ┌───────────┐  全部步骤成功   ┌───────────┐
     │  RUNNING  │───────────────→│ COMPLETED │
     └───────────┘                └───────────┘
     ┌───────────┐  部分步骤成功   ┌───────────┐
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
    step_index: int                # 当前 PlanStep 索引
    plan: Plan                     # 执行计划
    results: List[StepResult]      # 已完成步骤的结果
    contexts: dict                 # 上下文信息
    timestamp: float               # 快照时间戳
```

**持久化时机：**

| 时机 | 说明 |
|------|------|
| 每个 PlanStep 完成后 | 自动保存当前进度 |
| 状态变更时 | RUNNING → PAUSED / FAILED / TIMED_OUT |
| 异常恢复前 | 保存中断前的完整上下文 |
| 用户主动暂停时 | 立即持久化 |

**存储结构：**

```
snapshots/
├── task_{id}_latest.json          # 最新快照（用于恢复）
├── task_{id}_step_{n}.json        # 每个步骤的历史快照
└── task_{id}_checkpoint.json      # 关键检查点快照
```

**恢复流程：** 加载最新快照 → 重建 Task 对象 → 从断点步骤继续 → 重新感知页面状态 → 继续执行。

---

### 4.2 Workflow Engine（工作流引擎）

**职责：** 将高层任务目标分解为有序的 PlanStep 序列，并管理步骤间的流转。

**核心模型：**

```python
class Workflow:
    task_id: str                   # 关联的任务 ID
    plan: Plan                     # 执行计划
    current_step_index: int        # 当前步骤索引
    status: WorkflowStatus         # 工作流状态
```

**职责边界：**

| 模块 | 职责 |
|------|------|
| **Workflow Engine** | 决定"做哪些步骤、按什么顺序"（宏观编排） |
| **Planner** | 决定"当前步骤的下一步动作"（微观决策） |

**示例：** 任务"搜索 iOS 开发并投递前三个岗位"

```
Plan:
  Step 1: 打开 Boss 直聘 App
  Step 2: 进入搜索页面
  Step 3: 搜索 "iOS开发"
  Step 4: 浏览职位列表
  Step 5: 投递第一个职位
  Step 6: 投递第二个职位
  Step 7: 投递第三个职位
```

**步骤流转规则：**

| 当前步骤结果 | 下一步行为 |
|-------------|-----------|
| SUCCESS | 推进到下一步骤 |
| FAILED | 进入异常恢复流程 |
| SKIPPED | 标记跳过，推进到下一步骤 |

---

### 4.3 State Machine（状态机）

**职责：** 约束 Agent 在每个阶段允许的行为，防止不合理的状态转换。

**核心状态转换：**

```
INIT → OBSERVING → PLANNING → EXECUTING → VALIDATING → OBSERVING (循环)
                                                         │
                                               步骤完成 → STEP_COMPLETED
                                               任务完成 → TASK_COMPLETED
                                               异常     → RECOVERING → OBSERVING
```

**作用：** 防止 Agent 在未观察状态下直接执行动作，或在未验证状态下跳过检查。状态机确保每个循环阶段按序执行，不允许跳跃。

---

### 4.4 Perception Layer（感知层）

**职责：** 从设备获取当前页面状态，提供结构化的观察数据。

**组成：**

| 组件 | 职责 |
|------|------|
| **UI Parser** | 解析 WDA 返回的 UI 树结构 |
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

**感知流程：** 获取 UI 树 → 采集截图 → 计算 ObservationDiff → 输出 Observation

---

### 4.5 Planner（规划器）

**职责：** 基于当前状态做出 **局部决策**，决定下一步执行的动作。

> ⚠️ **关键约束：** Planner 只负责"下一步做什么"，**不负责长链规划**。长链路由 Workflow Engine 控制。

**输入：**

| 参数 | 说明 |
|------|------|
| Goal | 当前 Step 的目标描述 |
| CurrentState | 当前状态机状态 |
| PageContext | 当前页面上下文（Observation） |

**输出：**

```json
{
    "reason": "当前在搜索页面，需要点击搜索框以输入关键词",
    "action": "CLICK",
    "target": "搜索框"
}
```

**推荐模型：** GPT-4o Vision / Claude Sonnet

---

### 4.6 Executor（执行器）

**职责：** 将 Planner 输出的抽象动作翻译为 WDA 命令并执行。

**执行流程：** Action → 定位目标元素（通过 UI 树匹配语义描述）→ 调用 WDA API → 等待设备响应 → 返回 ActionRecord

---

### 4.7 Validator（验证器）

**职责：** 独立验证每个动作和步骤的执行结果。

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
│  验证：步骤目标是否达成                                       │
│  时机：PlanStep 完成时验证                                   │
│  示例：完成"登录"步骤 → 检查是否成功登录并进入首页           │
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
  (步骤完成时)
    │
 Level 3 验证
    │
┌───┴───┐
↓       ↓
✅ 通过  ❌ 失败 → 进入异常恢复
```

---

### 4.8 Memory（记忆系统）

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

### 4.9 Recovery Manager（异常恢复管理器）

**职责：** 根据错误类型和上下文，选择最优恢复策略。

#### 异常分类与恢复策略

| 异常类型 | 恢复策略 | 说明 |
|----------|----------|------|
| **页面未找到** | 重新识别 → 重新截图 → 重新规划 | 逐步降级，从轻量到重量 |
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
              ├── HIGH 严重度 → 跳过步骤或重新规划
              └── CRITICAL 严重度 → 终止任务
```

#### LLM 辅助恢复

对于 MEDIUM 及以上严重度的错误，使用 LLM 分析最佳恢复策略：

```
输入：错误信息 + 当前页面 + 已尝试恢复次数
输出：{"strategy": "replan", "reason": "当前页面与预期不符，建议重新规划"}
```

#### 恢复限制

| 限制项 | 阈值 | 说明 |
|--------|------|------|
| 单步骤最大重试次数 | 3 | 防止无限重试 |
| 单任务最大恢复次数 | 5 | 超出后终止任务 |
| 连续恢复失败阈值 | 5 | 可能卡死，建议人工介入 |

---

## 五、Agent 主循环

### 5.1 设计理念

Agent 的核心运行逻辑遵循 **Observe → Decide → Execute → Validate** 循环，并在每轮循环前加入前置检查（处理弹窗、键盘、加载状态），在循环结束后加入检查点保存和异常恢复。

### 5.2 完整流程

```
任务启动
  │
  ▼
init: 初始化环境
  │
  ▼
cleanup: 前置清理（弹窗 / 键盘）
  │
  ▼
plan: LLM 任务规划（生成 Plan）
  │
  ▼
refresh: 刷新屏幕状态
  │
  ▼
┌─── pre_check: 前置检测 ──────────────────────┐
│  有弹窗 → 自动处理弹窗 → refresh              │
│  有键盘 → 自动关闭键盘 → refresh              │
│  加载中 → 等待加载完成 → refresh              │
│  正常   → 进入决策                            │
└──────────────────────────────────────────────┘
  │
  ▼
decide: LLM 决策下一步
  │
  ├── 有操作 → execute: 执行工具调用 → verify
  └── 无操作 → verify: 验证步骤目标
  │
  ▼
┌─── verify: 三级验证 ─────────────────────────┐
│  passed → 还有步骤? → 是 → refresh（继续循环）│
│                       → 否 → summary          │
│  failed → recovery: LLM 恢复分析              │
│              ├── retry → refresh              │
│              ├── skip → 下一步骤              │
│              ├── abort → summary              │
│              └── timeout → summary            │
└──────────────────────────────────────────────┘
  │
  ▼
summary: 生成执行报告 → 任务结束
```

### 5.3 前置检查机制

在每轮"决策-执行"前，自动检测并处理干扰因素：

| 检测项 | 处理方式 | 后续动作 |
|--------|----------|----------|
| 弹窗 (Alert) | 查找关闭按钮（"关闭"、"取消"、"知道了"等）自动关闭 | 重新观察 |
| 键盘 (Keyboard) | 点击空白区域收起键盘 | 重新观察 |
| 加载状态 (Loading) | 等待加载完成（关键词检测："加载中"、"请稍候"等） | 重新观察 |
| 无法处理 | 返回 ABORT，进入异常恢复 | 恢复流程 |

**前置检查结果：**

| 结果 | 含义 |
|------|------|
| `NORMAL` | 正常，继续执行决策 |
| `HANDLED` | 已处理干扰因素，重新观察 |
| `WAIT` | 需要等待（加载中），延迟后重新观察 |
| `ABORT` | 无法处理，进入异常恢复 |

### 5.4 单步骤执行逻辑

每个 PlanStep 的执行是一个内部动作循环：

```
单步骤执行：
  1. 前置清理（弹窗 / 键盘 / 加载）
  2. 观察（获取 Observation + ObservationDiff）
  3. 前置检查（处理干扰因素）
  4. 决策（Planner 输出 Action，若无动作则尝试验证步骤目标）
  5. 执行（Executor 调用 WDA）
  6. 验证（三级验证）
     - 通过 → 继续循环或步骤完成
     - 失败 → Recovery Manager 介入
        - RETRY → 回到步骤 1
        - SKIP_STEP → 标记跳过，步骤结束
        - ABORT_TASK → 步骤失败，任务终止
  7. 动作计数检查（单步骤最多 10 个动作）
```

---

## 六、并发与异步设计

### 6.1 异步架构

Agent 主循环采用异步设计，在等待设备响应和 LLM 响应时让出控制权：

| 操作 | 异步方式 | 说明 |
|------|----------|------|
| 观察 (observe) | `await` | 等待 WDA 返回 UI 树和截图 |
| 决策 (decide) | `await` | 等待 LLM 响应 |
| 执行 (execute) | `await` | 等待 WDA 命令执行完成 |
| 验证 (validate) | `await` | 等待页面变化确认 |

### 6.2 并发约束

| 维度 | 约束 | 原因 |
|------|------|------|
| **任务级** | 单 Agent 单任务 | 避免状态冲突，简化调试 |
| **步骤级** | 串行执行 | Workflow 有依赖关系，不能乱序 |
| **动作级** | 串行执行 | WDA 不支持并发命令 |
| **观察级** | 可异步 | 等待设备响应时可让出控制权 |
| **LLM 调用** | 可异步 | 等待 LLM 响应时可让出控制权 |

### 6.3 资源隔离

每个 Task 分配独立的资源目录，防止并发执行时的资源冲突：

```
task_{id}/
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

每个 Agent 独立消费任务队列中的任务，通过资源隔离确保互不干扰。

---

## 七、Agent 状态管理

### 7.1 AgentState 结构

```python
class AgentState:
    task_id: str                           # 当前任务 ID
    task_status: TaskStatus                # 任务状态
    current_step_index: int                # 当前步骤索引
    plan: Plan                             # 执行计划
    last_observation: Observation          # 最近一次观察结果
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
    completed_steps: int = 0               # 完成步骤数
    skipped_steps: int = 0                 # 跳过步骤数
    failed_steps: int = 0                  # 失败步骤数
    recovery_attempts: int = 0             # 恢复尝试次数
    recovery_success_rate: float = 1.0     # 恢复成功率
    screenshot_count: int = 0              # 截图次数
    llm_call_duration: float = 0.0         # LLM 调用总耗时
    llm_token_usage: int = 0               # LLM Token 总用量
    wda_call_duration: float = 0.0         # WDA 调用总耗时
```

### 7.3 健康监控

通过 StateMonitor 实时检测 Agent 运行健康状态：

| 检查项 | 阈值 | 诊断 |
|--------|------|------|
| 连续恢复次数 | ≥ 5 | 可能卡死，建议终止任务或重启应用 |
| 任务运行时长 | > 30 分钟 | 运行时间过长，建议检查执行状态 |
| 恢复成功率 | < 50%（且恢复次数 > 5） | 恢复策略效果差，建议重新规划或终止 |
| 空闲时间 | > 1 分钟无活动 | 可能卡死，建议检查 Agent 状态 |

---

## 八、Prompt 设计

### 8.1 系统 Prompt 模板

```text
你是一个 iOS 自动化测试 Agent。

## 目标
完成当前 Step: {step_description}

## 当前页面
- 页面名称: {page_name}
- 可交互元素: {elements_list}
- 页面元数据: {metadata}

## 历史动作
{action_history}

## 规则
1. 只能从候选 Action 中选择动作
2. 不允许跳过 Step
3. 不允许执行无关动作
4. 优先使用 UI Tree 信息
5. UI Tree 不可用时使用 Screenshot
6. 如果认为当前 Step 已完成，返回 null

## 输出格式
{
    "reason": "决策理由",
    "action": "CLICK",
    "target": "登录"
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
├── wda/                     # WDA 通信
│   └── client.py            #   WDA 客户端
└── main.py                  # 入口文件
```

---

## 附录 A：核心数据模型完整字段参考

### A.1 UIElement 完整属性

| 属性 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | 元素唯一标识 |
| `type` | `ElementType` | 元素类型（枚举见 3.2 节） |
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
| `RUNNING` | `COMPLETED` | 全部步骤成功 |
| `RUNNING` | `PARTIAL` | 部分步骤成功 |
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
当前步骤: {current_step} / {total_steps}

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
  - WDA 调用耗时: {wda_duration}s

资源使用:
  - 截图次数: {screenshot_count}
  - LLM Token: {llm_token_usage}
```
