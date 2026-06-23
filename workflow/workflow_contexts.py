"""工作流上下文 — DeviceContext / TaskContext / LLMContext

按职责拆分为三个独立上下文，节点按需注入，避免单一巨型 Context。
"""

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from wda_client import WDAClient
from core.screen_monitor import ScreenMonitor
from core.context_manager import MessageContextManager
from hello_agents import HelloAgentsLLM

if TYPE_CHECKING:
    from hello_agents.tools.registry import ToolRegistry


# ---------------------------------------------------------------------------
# DeviceContext
# ---------------------------------------------------------------------------

@dataclass
class DeviceContext:
    """设备上下文：WDA 连接和屏幕状态

    职责：
    - 持有 WDAClient 实例
    - 持有 ScreenMonitor 实例
    - 提供设备级操作的快捷入口
    """
    wda: WDAClient = None 
    screen_monitor: ScreenMonitor = None


# ---------------------------------------------------------------------------
# TaskContext
# ---------------------------------------------------------------------------

@dataclass
class TaskContext:
    """任务上下文：任务信息和执行状态

    职责：
    - 持有原始任务描述
    - 管理结构化操作计划
    - 跟踪当前步骤和执行进度
    - 统计 LLM 调用次数和 Token 消耗
    - 管理恢复计数和硬性护栏
    """
    task: str = ""
    plan: Optional[dict] = None
    current_step_index: int = 0
    step_results: List[dict] = field(default_factory=list)
    all_step_results: List[dict] = field(default_factory=list)
    total_recoveries: int = 0
    consecutive_recoveries: int = 0
    global_steps: int = 0
    max_steps: int = 30

    stats: Dict[str, Any] = field(default_factory=lambda: {
        "llm_calls": 0,
        "total_tokens": 0,
    })

    # 工具相关
    tool_registry: Optional[Any] = None
    tool_filter: Optional[Any] = None

    # 任务状态
    status: str = "running"  # "running" | "completed" | "partial" | "aborted"
    summary: str = ""

    # 当前操作（由 DecideReasoning 写入，ExecuteAction 读取）
    current_operation: Optional[Any] = None
    
    # 恢复建议（由 RecoveryReasoning 写入，DecideReasoning 读取）
    recovery_suggestion: Optional[str] = None

    # 最近一次失败原因（由 VerifyCheckpoint 写入，RecoveryReasoning 读取）
    last_failure_reason: str = ""

    # 时间
    started_at: float = field(default_factory=time.time)
    _state_path: str = ".workflow_state.json"

    # ----- 计划操作 -----

    def get_current_step(self) -> Optional[dict]:
        """获取当前步骤"""
        if not self.plan or not self.plan.get("steps"):
            return None
        steps = self.plan["steps"]
        if self.current_step_index >= len(steps):
            return None
        return steps[self.current_step_index]

    def advance_step(self):
        """推进到下一步"""
        self.current_step_index += 1

    def is_all_steps_completed(self) -> bool:
        """检查是否所有步骤都已完成"""
        if not self.plan or not self.plan.get("steps"):
            return True
        return self.current_step_index >= len(self.plan["steps"])

    def increment_recovery_count(self):
        """递增恢复计数"""
        self.total_recoveries += 1
        self.consecutive_recoveries += 1

    def reset_consecutive_recoveries(self):
        """重置连续恢复计数（步骤成功时调用）"""
        self.consecutive_recoveries = 0

    def increment_llm_call(self, tokens: int = 0):
        """递增 LLM 调用统计"""
        self.stats["llm_calls"] += 1
        self.stats["total_tokens"] += tokens

    def elapsed_seconds(self) -> float:
        """获取任务已运行时长（秒）"""
        return time.time() - self.started_at

    def format_plan_progress(self) -> str:
        """格式化计划进度为可读文本"""
        if not self.plan or not self.plan.get("steps"):
            return "（无计划）"

        lines = []
        for i, step in enumerate(self.plan["steps"]):
            prefix = "✅" if i < self.current_step_index else "🔄" if i == self.current_step_index else "⬜"
            lines.append(f"  {prefix} 步骤 {step.get('id', i+1)}: {step.get('description', '?')}")
        return "\n".join(lines)

    # ----- 状态持久化 -----

    def save_state(self):
        """保存工作流状态到文件"""
        from .workflow_engine import WorkflowState
        state = WorkflowState(
            task=self.task,
            plan=self.plan,
            current_node="",  # 由引擎填写
            current_step_index=self.current_step_index,
            step_results=self.all_step_results[-5:],  # 只保留最近 5 条
            total_recoveries=self.total_recoveries,
            stats=self.stats,
            started_at=datetime.fromtimestamp(self.started_at).isoformat(),
            last_updated_at=datetime.now().isoformat(),
        )
        try:
            state.save(self._state_path)
        except Exception:
            pass  # 持久化失败不应中断工作流

    @classmethod
    def load_state(cls, path: str) -> Optional["TaskContext"]:
        """从文件恢复任务上下文"""
        try:
            from .workflow_engine import WorkflowState
            state = WorkflowState.load(path)
            ctx = cls(task=state.task)
            ctx.plan = state.plan
            ctx.current_step_index = state.current_step_index
            ctx.total_recoveries = state.total_recoveries
            ctx.stats = state.stats
            return ctx
        except Exception:
            return None

    def clean_state(self):
        """清理状态文件（任务完成或终止时调用）"""
        import os
        try:
            if os.path.exists(self._state_path):
                os.remove(self._state_path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# LLMContext
# ---------------------------------------------------------------------------

@dataclass
class LLMContext:
    """LLM 上下文：模型和消息管理

    职责：
    - 持有 LLM 实例
    - 管理消息历史
    - 持有 MessageContextManager（屏幕状态注入）
    """
    llm: HelloAgentsLLM = NotImplemented
    messages: List[dict] = field(default_factory=list)
    context_manager: MessageContextManager = None
