"""WorkflowEngine — 结构化工作流引擎

驱动节点（Routine / Reasoning / Checkpoint / Action）的执行和状态转移。
支持同步和异步两套 API，兼容现有 StreamEvent 机制。
"""

import asyncio
import inspect
import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from hello_agents.core.streaming import StreamEvent, StreamEventType


# ---------------------------------------------------------------------------
# Node result types
# ---------------------------------------------------------------------------

@dataclass
class NodeResult:
    """节点执行结果基类"""
    status: str  # "success" | "failed" | "timeout" | ...
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"status": self.status, "data": self.data}


@dataclass
class RoutineResult(NodeResult):
    pass


@dataclass
class ReasoningResult(NodeResult):
    pass


@dataclass
class CheckpointResult(NodeResult):
    pass


@dataclass
class ActionResult(NodeResult):
    pass


# ---------------------------------------------------------------------------
# Node timeout configuration
# ---------------------------------------------------------------------------

class NodeTimeout:
    """节点超时配置

    默认值基于常见场景设定，可通过 Config 或环境变量覆盖。
    LLM 节点（plan/decide/recovery）的超时建议根据实际模型速度调整。
    """
    DEFAULT_TIMEOUTS = {
        "init":      10.0,
        "cleanup":    5.0,
        "plan":      30.0,
        "refresh":    5.0,
        "pre_check":  5.0,
        "decide":    30.0,
        "execute":   15.0,
        "verify":    15.0,
        "recovery":  30.0,
        "summary":   10.0,
    }

    def __init__(self, overrides: Optional[Dict[str, float]] = None):
        self._timeouts = {**self.DEFAULT_TIMEOUTS, **(overrides or {})}

    def get(self, node_id: str) -> float:
        return self._timeouts.get(node_id, 30.0)


# ---------------------------------------------------------------------------
# Persistent workflow state
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """可持久化的工作流状态"""
    task: str = ""
    plan: Optional[dict] = None
    current_node: str = ""
    current_step_index: int = 0
    step_results: List[dict] = field(default_factory=list)
    total_recoveries: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    last_updated_at: str = ""

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False, default=str)

    @classmethod
    def load(cls, path: str) -> "WorkflowState":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)


# ---------------------------------------------------------------------------
# WorkflowEngine
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """工作流引擎：驱动节点执行和状态转移

    提供同步和异步两套 API：
    - run(): 同步执行，供 WorkflowAgent._run_workflow() 直接调用
    - arun_stream(): 异步流式执行，供 WorkflowAgent._arun_workflow() 使用
    """

    def __init__(
        self,
        node_timeout: Optional[NodeTimeout] = None,
        state_path: str = ".workflow_state.json",
        global_max_steps: int = 100,
    ):
        self._nodes: Dict[str, Any] = {}
        self._transitions: Dict[str, Dict[str, str]] = {}
        self._start_node: Optional[str] = None
        self._node_order: List[str] = []

        self._node_timeout = node_timeout or NodeTimeout()
        self._state_path = state_path
        self._global_max_steps = global_max_steps

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register_node(self, node_id: str, node: Any):
        """注册工作流节点"""
        self._nodes[node_id] = node
        self._node_order.append(node_id)

    def add_transition(self, from_node: str, status: str, to_node: str):
        """定义节点间的状态转移规则"""
        self._transitions.setdefault(from_node, {})[status] = to_node

    def set_start(self, node_id: str):
        """设置起始节点"""
        self._start_node = node_id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_next_node(self, node_id: str, status: str) -> Optional[str]:
        """根据当前节点和执行结果决定下一个节点"""
        transitions = self._transitions.get(node_id, {})
        next_node = transitions.get(status)
        if next_node is None and status not in transitions:
            # Fallback: try "timeout" → "recovery" if defined
            next_node = transitions.get("timeout")
        return next_node

    def _inject_contexts(self, node: Any, device_ctx, task_ctx, llm_ctx) -> dict:
        """根据节点 execute() 签名自动注入所需上下文

        通过 inspect.signature 检查节点的 execute 方法需要哪些参数，
        从三个 Context 中按需注入，避免每个节点都接收全部上下文。
        """
        sig = inspect.signature(node.execute)
        kwargs = {}
        param_map = {
            "device_ctx": device_ctx,
            "task_ctx": task_ctx,
            "llm_ctx": llm_ctx,
        }
        for name in sig.parameters:
            if name in param_map:
                kwargs[name] = param_map[name]
        return kwargs

    def _increment_global_step(self, task_ctx):
        """全局步数计数（兜底保护）"""
        task_ctx.global_steps = getattr(task_ctx, "global_steps", 0) + 1
        return task_ctx.global_steps <= self._global_max_steps

    # ------------------------------------------------------------------
    # Synchronous execution
    # ------------------------------------------------------------------

    def run(self, device_ctx, task_ctx, llm_ctx) -> str:
        """同步执行工作流（阻塞直到完成）"""
        node_id = self._start_node
        if node_id is None:
            raise RuntimeError("WorkflowEngine: 未设置起始节点，请先调用 set_start()")

        while node_id:
            node = self._nodes.get(node_id)
            if node is None:
                raise RuntimeError(f"WorkflowEngine: 未知节点 '{node_id}'")

            print(f"  ▶ [{type(node).__name__}] {node_id}")

            kwargs = self._inject_contexts(node, device_ctx, task_ctx, llm_ctx)

            timeout = self._node_timeout.get(node_id)
            result_holder: List[NodeResult] = []
            exc_holder: List[Exception] = []

            def _run_node():
                try:
                    result_holder.append(node.execute(**kwargs))
                except Exception as e:
                    exc_holder.append(e)

            t = threading.Thread(target=_run_node, daemon=True)
            t.start()
            t.join(timeout=timeout)

            if t.is_alive():
                result = NodeResult(status="timeout", data={"node": node_id})
                print(f"  ⏱ 节点 '{node_id}' 超时 ({timeout}s)")
            elif exc_holder:
                result = NodeResult(status="failed", data={
                    "node": node_id, "error": str(exc_holder[0])
                })
                print(f"  ❌ 节点 '{node_id}' 执行异常: {exc_holder[0]}")
            elif result_holder:
                result = result_holder[0]
            else:
                result = NodeResult(status="failed", data={"node": node_id, "error": "no result"})

            # 保存状态
            task_ctx.save_state()

            # 全局步数保护
            if not self._increment_global_step(task_ctx):
                print(f"  ⚠️ 全局步数上限 ({self._global_max_steps}) 已达，强制终止")
                node_id = self._get_next_node(node_id, "abort")
                if node_id is None:
                    break
                continue

            next_id = self._get_next_node(node_id, result.status)
            if next_id is None:
                # 无转移规则，任务结束
                break
            node_id = next_id

        return task_ctx.summary or "任务完成"

    # ------------------------------------------------------------------
    # Async streaming execution
    # ------------------------------------------------------------------

    async def arun_stream(self, device_ctx, task_ctx, llm_ctx):
        """异步流式执行工作流

        节点的 execute() 是同步方法，通过 run_in_executor 包装为异步。
        yield StreamEvent 供上层 UI 和监控系统消费。
        """
        node_id = self._start_node
        if node_id is None:
            raise RuntimeError("WorkflowEngine: 未设置起始节点")

        loop = asyncio.get_event_loop()

        while node_id:
            node = self._nodes.get(node_id)
            if node is None:
                raise RuntimeError(f"WorkflowEngine: 未知节点 '{node_id}'")

            yield StreamEvent.create(
                StreamEventType.STEP_START,
                self.__class__.__name__,
                node=node_id,
                node_type=type(node).__name__,
            )

            kwargs = self._inject_contexts(node, device_ctx, task_ctx, llm_ctx)
            timeout = self._node_timeout.get(node_id)

            try:
                # Capture kwargs via default args to avoid closure late-binding
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda n=node, kw=kwargs: n.execute(**kw)
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                result = NodeResult(status="timeout", data={"node": node_id})
            except Exception as e:
                result = NodeResult(status="failed", data={"node": node_id, "error": str(e)})

            yield StreamEvent.create(
                StreamEventType.STEP_FINISH,
                self.__class__.__name__,
                node=node_id,
                result=result.to_dict(),
            )

            task_ctx.save_state()

            if not self._increment_global_step(task_ctx):
                print(f"  ⚠️ 全局步数上限 ({self._global_max_steps}) 已达，强制终止")
                node_id = self._get_next_node(node_id, "abort")
                if node_id is None:
                    break
                continue

            node_id = self._get_next_node(node_id, result.status)
            if node_id is None:
                break


# ---------------------------------------------------------------------------
# Default iOS workflow builder (assembled in project-level code)
# ---------------------------------------------------------------------------

def build_ios_workflow(
    node_timeout: Optional[NodeTimeout] = None,
    global_max_steps: int = 100,
) -> WorkflowEngine:
    """构建标准 iOS 自动化工作流

    节点实现从项目中导入，此处只负责注册和连接转移规则。
    实际的节点类在调用方组装时传入。
    """
    engine = WorkflowEngine(
        node_timeout=node_timeout,
        global_max_steps=global_max_steps,
    )

    # 转移规则在此处定义；节点实例由外部注册
    engine.add_transition("init",      "success",  "cleanup")
    engine.add_transition("cleanup",   "success",  "plan")
    engine.add_transition("plan",      "success",  "refresh")

    # 子步骤循环
    engine.add_transition("refresh",   "success",  "pre_check")
    engine.add_transition("pre_check", "success",  "decide")
    engine.add_transition("decide",    "success",  "execute")
    engine.add_transition("decide",    "no_action", "verify")
    engine.add_transition("execute",   "executed", "verify")

    # 验证分支
    engine.add_transition("verify",    "passed",    "refresh")
    engine.add_transition("verify",    "failed",    "recovery")
    engine.add_transition("verify",    "completed", "summary")

    # 恢复分支
    engine.add_transition("recovery",  "retry",     "decide")
    engine.add_transition("recovery",  "skip",      "refresh")
    engine.add_transition("recovery",  "abort",     "summary")

    engine.set_start("init")
    return engine
