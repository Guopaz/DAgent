"""WorkflowAgent — 基于结构化工作流的 Agent 基类

与 ReActAgent 的区别：
- ReActAgent: 每步都是 LLM 自由决策的 ReAct 循环
- WorkflowAgent: 由 WorkflowEngine 驱动固定节点编排，LLM 只在 Reasoning 节点参与

与 PlanSolveAgent 的区别：
- PlanSolveAgent: 规划后每步只做一次 LLM 调用，无工具循环
- WorkflowAgent: 规划后每步进入结构化循环（Routine → Reasoning → Action → Checkpoint）

继承自 Agent 基类，复用：
- HistoryManager: 历史管理
- ObservationTruncator: 工具输出截断
- TraceLogger: 可观测性
- ToolRegistry: 工具管理
- SkillLoader: 知识外化
"""

import asyncio
from typing import Optional, TYPE_CHECKING

from hello_agents.core.agent import Agent
from hello_agents.core.config import Config
from hello_agents.core.llm import HelloAgentsLLM

from .workflow_engine import WorkflowEngine
from .workflow_contexts import DeviceContext, TaskContext, LLMContext

if TYPE_CHECKING:
    from hello_agents.tools.registry import ToolRegistry


class WorkflowAgent(Agent):
    """
    WorkflowAgent - 基于结构化工作流的 Agent 基类

    子类需要：
    1. 构建 WorkflowEngine 并传入
    2. 实现 run() / arun() 方法，构建 Context 后调用 _run_workflow()
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        workflow: WorkflowEngine,
        tool_registry: Optional['ToolRegistry'] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_steps: int = 30,
    ):
        super().__init__(
            name=name,
            llm=llm,
            system_prompt=system_prompt,
            config=config,
            tool_registry=tool_registry,
        )
        self.workflow = workflow
        self.max_steps = max_steps

    def run(self, task: str, **kwargs) -> str:
        """
        执行工作流任务

        子类应覆写此方法以构建特定的 DeviceContext / TaskContext / LLMContext，
        然后调用 _run_workflow() 驱动引擎执行。

        Args:
            task: 用户任务描述

        Returns:
            任务执行结果摘要
        """
        raise NotImplementedError("子类应实现 run() 方法")

    def _run_workflow(
        self,
        device_ctx: DeviceContext,
        task_ctx: TaskContext,
        llm_ctx: LLMContext,
    ) -> str:
        """
        驱动工作流引擎执行（同步版本）

        Args:
            device_ctx: 设备上下文（WDA、屏幕监听器）
            task_ctx: 任务上下文（任务描述、计划、状态）
            llm_ctx: LLM 上下文（模型、消息、上下文管理器）

        Returns:
            任务执行结果摘要
        """
        task_ctx.max_steps = self.max_steps

        final_result = self.workflow.run(device_ctx, task_ctx, llm_ctx)

        self._session_metadata["total_steps"] = task_ctx.current_step_index
        self._session_metadata["total_tokens"] = task_ctx.stats.get("total_tokens", 0)
        self._session_metadata["total_llm_calls"] = task_ctx.stats.get("llm_calls", 0)
        self._session_metadata["total_recoveries"] = task_ctx.total_recoveries

        return final_result

    async def _arun_workflow(
        self,
        device_ctx: DeviceContext,
        task_ctx: TaskContext,
        llm_ctx: LLMContext,
    ) -> str:
        """
        驱动工作流引擎执行（异步版本）

        适用于已在事件循环中运行的场景，直接 await 异步引擎。
        如需流式事件，子类应覆写 arun() 并使用 stream=True。

        Returns:
            任务执行结果摘要
        """
        task_ctx.max_steps = self.max_steps

        async for event in self.workflow.arun_stream(device_ctx, task_ctx, llm_ctx):
            pass  # 事件已通过 StreamEvent 机制分发

        self._session_metadata["total_steps"] = task_ctx.current_step_index
        self._session_metadata["total_tokens"] = task_ctx.stats.get("total_tokens", 0)
        self._session_metadata["total_llm_calls"] = task_ctx.stats.get("llm_calls", 0)
        self._session_metadata["total_recoveries"] = task_ctx.total_recoveries

        return task_ctx.summary

    async def arun(self, task: str, **kwargs) -> str:
        """
        异步执行工作流任务

        覆写基类 arun()，构建 Context 后调用 _arun_workflow()。
        子类应覆写此方法以构建特定的 DeviceContext / TaskContext / LLMContext。

        Returns:
            任务执行结果摘要
        """
        raise NotImplementedError(
            "子类应实现 arun()，构建 Context 后调用 _arun_workflow()"
        )
