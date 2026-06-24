"""自动从旧 agent.py 拆分生成；按职责维护。"""

from __future__ import annotations

import base64
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from agent.models import *
from agent.device.factory import ensure_device
from agent.device.mock import MockDevice
from agent.perception.layer import PerceptionLayer
from agent.planner import Planner
from agent.executor import Executor
from agent.validator import Validator
from agent.memory import Memory
from agent.recovery_manager import RecoveryManager
from agent.state_machine import StateMachine
from agent.workflow.workflow import Workflow
from agent.workflow.workflow_engine import WorkflowEngine
from agent.helpers import _compact_observation, _safe_asdict

class AgentLoop:
    def __init__(
        self,
        wda: Any = None,
        perception: Optional[PerceptionLayer] = None,
        planner: Optional[Planner] = None,
        executor: Optional[Executor] = None,
        validator: Optional[Validator] = None,
        recovery: Optional[RecoveryManager] = None,
        memory: Optional[Memory] = None,
        max_actions_per_step: int = 10,
        max_consecutive_failures: int = 5,
        artifact_root: str | Path = ".artifacts",
        snapshot_dir: str | Path | None = None,
    ):
        self.device = ensure_device(wda) if wda is not None else None
        self.perception = perception or PerceptionLayer(self.device or MockDevice())
        self.planner = planner or Planner()
        self.executor = executor or Executor(self.device or MockDevice())
        self.validator = validator or Validator()
        self.recovery = recovery or RecoveryManager(self.device)
        self.memory = memory or Memory()
        self.workflow_engine = WorkflowEngine()
        self.state_machine = StateMachine()
        self.max_actions_per_step = max_actions_per_step
        self.max_consecutive_failures = max_consecutive_failures
        # 设计方案 6.3：每个任务使用 .artifacts/task_{id}/ 独立资源目录。
        # snapshot_dir 仅保留兼容旧调用；新实现不再把快照散落到仓库根目录 snapshots/。
        self.artifact_root = Path(snapshot_dir).parent if snapshot_dir else Path(artifact_root)
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.current_task_dir: Optional[Path] = None
        self.agent_state = AgentState()
        self.agent_stats = AgentStats()

    def run_task(self, task: Task) -> bool:
        workflow = self.workflow_engine.create_workflow(task)
        self._prepare_task_resources(task, workflow)
        task.status = TaskStatus.RUNNING
        task.metrics.started_at = time.time()
        self.agent_state = AgentState(
            task_id=task.id,
            task_status=task.status,
            task_goal=workflow.goal,
            progress=task.progress,
            current_round=0,
            current_node="init",
            started_at=task.metrics.started_at,
            last_active_at=time.time(),
        )
        self.agent_stats = AgentStats()
        self.state_machine.reset()  # 重置状态机，确保从 INIT 状态开始
        self._write_event(task, "task_started", {"goal": task.goal, "params": task.params})
        self._save_state_report(task, workflow, last_observation=None)
        consecutive_failures = 0
        last_action_context: Optional[ActionContext] = None
        round_index = 0
        last_observation: Optional[Observation] = None

        print(f"▶️  开始任务：{task.goal}")
        if self.current_task_dir:
            print(f"📁 任务资源目录：{self.current_task_dir}")
        while True:
            round_started = time.time()
            round_index += 1
            self.agent_state.current_round = round_index
            self.agent_state.current_node = "round_start"
            self.agent_state.last_active_at = time.time()
            task.updated_at = datetime.now()

            if time.time() - (task.metrics.started_at or time.time()) > workflow.goal.timeout:
                task.status = TaskStatus.TIMED_OUT
                self.agent_state.task_status = task.status
                self.agent_state.current_node = "timed_out"
                self._save_state_report(task, workflow, last_observation=last_observation)
                print("⏰ 任务超时")
                break
            if task.progress.action_count >= workflow.goal.max_actions:
                task.status = TaskStatus.FAILED
                self.agent_state.task_status = task.status
                self.agent_state.current_node = "max_actions_reached"
                self._save_state_report(task, workflow, last_observation=last_observation)
                print("⛔ 达到最大动作数，终止任务")
                break

            try:
                self.state_machine.transition(AgentRunState.OBSERVING)
                observation_before = self.perception.observe()
                last_observation = observation_before
                self.agent_state.current_node = "observing"
                self.agent_state.last_observation = observation_before
                self.agent_state.device_status = observation_before.device_status
                self.agent_state.device_info = observation_before.device_info
                self.agent_stats.screenshot_count += 1 if observation_before.screenshot_path else 0
                self.memory.remember_page(observation_before)
                self._save_observation(task, round_index, "before", observation_before)
                self._write_event(task, "observed_before", {
                    "round": round_index,
                    "page_name": observation_before.page_name,
                    "element_count": len(observation_before.elements),
                    "screenshot_path": observation_before.screenshot_path,
                })
                print(f"\n🔎 Round {round_index} 页面：{observation_before.page_name}，元素数：{len(observation_before.elements)}")

                if observation_before.diff_from_previous.has_alert:
                    print("⚠️ 检测到弹窗，交由 Planner/Recovery 后续处理")
                if observation_before.diff_from_previous.is_loading:
                    self.perception.device.wait(1.0)

                self.state_machine.transition(AgentRunState.PLANNING)
                context = workflow.build_decision_context(
                    observation_before,
                    observation_before.device_status,
                    observation_before.device_info,
                    self.memory,
                    self.state_machine.state,
                )
                decision = self.planner.decide(context, last_action_context)
                workflow.progress.last_decision = decision
                self.agent_state.current_node = "planning"
                self.agent_state.last_decision = decision
                self.agent_stats.decision_rounds = max(self.agent_stats.decision_rounds, round_index)
                # 先输出验证结果（如果有），再输出决策
                if decision.validation:
                    print(f"🏹 验证：{decision.validation.passed} - {decision.validation.reason}")

                self._write_event(task, "decision", {"round": round_index, "decision": _safe_asdict(decision)})
                if decision.page_summary:
                    print(f"📄 页面：{decision.page_summary}")
                print(f"🧭 决策：{decision.type.value} - {decision.reason}")

                action_record: Optional[ActionRecord] = None
                if decision.type == DecisionType.COMPLETE:
                    self.state_machine.transition(AgentRunState.VALIDATING)
                    validation = self.validator.validate(
                        decision,
                        None,
                        observation_before,
                        observation_before,
                        workflow.goal,
                        progress=workflow.progress,
                        memory=self.memory,
                        llm_validation=decision.validation,
                    )
                    self._write_event(task, "final_validation", {"round": round_index, "validation": _safe_asdict(validation)})
                    if validation.passed:
                        task.status = TaskStatus.COMPLETED
                        self.agent_state.task_status = task.status
                        self.agent_state.current_node = "task_completed"
                        self.agent_stats.completed_objectives = len(workflow.progress.completed_objectives)
                        self.state_machine.transition(AgentRunState.TASK_COMPLETED)
                        self._save_state_report(task, workflow, last_observation=observation_before)
                        print("✅ 任务完成")
                        break
                    decision = NextDecision(DecisionType.RECOVER, reason="Planner 判断完成，但 Validator 未确认")

                if decision.type == DecisionType.ABORT:
                    task.status = TaskStatus.ABORTED
                    self.agent_state.task_status = task.status
                    self.agent_state.current_node = "aborted"
                    self._save_state_report(task, workflow, last_observation=last_observation)
                    print(f"🛑 任务中止：{decision.reason}")
                    break

                if decision.type == DecisionType.RECOVER:
                    self.state_machine.transition(AgentRunState.RECOVERING)
                    strategy = self.recovery.recover(context)
                    task.metrics.recovery_count += 1
                    self.agent_state.current_node = "recovering"
                    self.agent_state.total_recoveries = task.metrics.recovery_count
                    self.agent_state.consecutive_recoveries += 1
                    self.agent_stats.recovery_attempts = task.metrics.recovery_count
                    self.memory.recoveries.append({"round": round_index, "strategy": strategy.value, "reason": decision.reason})
                    self._write_event(task, "recovery", {"round": round_index, "strategy": strategy.value, "reason": decision.reason})
                    if strategy == RecoveryStrategy.ABORT_TASK:
                        task.status = TaskStatus.FAILED
                        self.agent_state.task_status = task.status
                        self.agent_state.current_node = "recovery_abort"
                        self._save_state_report(task, workflow, last_observation=last_observation)
                        break
                    self.state_machine.transition(AgentRunState.OBSERVING)
                    continue

                if decision.type == DecisionType.WAIT:
                    action = Action(ActionType.WAIT, target="页面", value="2")
                    decision.action = action
                else:
                    action = decision.action
                    if not action:
                        raise RuntimeError("ACTION 决策缺少 action")

                self.state_machine.transition(AgentRunState.EXECUTING)
                action_record = self.executor.execute(action, observation_before)
                task.progress.action_count += 1
                task.metrics.action_count += 1
                self.agent_state.current_node = "executing"
                self.agent_stats.total_actions = task.metrics.action_count
                self.agent_stats.device_call_duration += action_record.duration
                self._write_event(task, "action_executed", {"round": round_index, "action_record": _safe_asdict(action_record)})
                target_desc = action.target
                if action.element_id:
                    target_desc = f"{target_desc} [{action.element_id}]" if target_desc else action.element_id
                print(f"🕹️  执行：{action.type.value} target='{target_desc}' result={action_record.result.success}")

                # 给页面一点反应时间，再重新观察。
                self.perception.device.wait(0.8)
                observation_after = self.perception.observe()
                last_observation = observation_after
                self.agent_state.last_observation = observation_after
                self.agent_state.device_status = observation_after.device_status
                self.agent_state.device_info = observation_after.device_info
                self.agent_stats.screenshot_count += 1 if observation_after.screenshot_path else 0
                self._save_observation(task, round_index, "after", observation_after)
                action_record.screenshot_after = observation_after.screenshot_path
                self._write_event(task, "observed_after", {
                    "round": round_index,
                    "page_name": observation_after.page_name,
                    "element_count": len(observation_after.elements),
                    "screenshot_path": observation_after.screenshot_path,
                })

                self.state_machine.transition(AgentRunState.VALIDATING)
                validation = self.validator.validate(decision, action_record, observation_before, observation_after, workflow.goal, llm_validation=decision.validation)
                self.agent_state.current_node = "validating"
                if validation.passed and action_record.result.success:
                    self.agent_stats.successful_actions += 1
                else:
                    self.agent_stats.failed_actions += 1
                    self.agent_stats.failed_rounds += 1
                self._write_event(task, "validation", {"round": round_index, "validation": _safe_asdict(validation)})
                # print(f"🧪 本轮验证：{validation.passed} - {validation.message}")
                
                if action_record:
                    self.memory.remember_action(action_record, validation)
                
                # 构建下一步的 ActionContext
                last_action_context = ActionContext(
                    action_type=action.type.value,
                    action_target=action.target,
                    action_value=action.value,
                    page_before=observation_before.page_name,
                    expected_outcome=decision.expected_outcome,
                    execution_result="success" if action_record.result.success else "failed"
                )
                record = ProgressRecord(
                    round_index=round_index,
                    focus=workflow.progress.current_focus,
                    decision=decision,
                    action_record=action_record,
                    validation=validation,
                    observation_before=observation_before,
                    observation_after=observation_after,
                    duration=time.time() - round_started,
                )
                task.results.append(record)

                if validation.passed:
                    consecutive_failures = 0
                    self._update_progress(workflow.progress, decision, validation)
                    self.agent_state.current_node = "progress_updated"
                    self.agent_state.progress = workflow.progress
                    self.agent_state.consecutive_recoveries = 0
                    self.agent_stats.completed_objectives = len(workflow.progress.completed_objectives)
                    self.state_machine.transition(AgentRunState.PROGRESS_UPDATED)
                    self._save_snapshot(task, workflow, observation_after, round_index=round_index, checkpoint=True)
                    self._save_state_report(task, workflow, last_observation=observation_after)
                    self.state_machine.transition(AgentRunState.OBSERVING)
                else:
                    consecutive_failures += 1
                    task.metrics.failure_count += 1
                    self.agent_stats.failed_rounds += 1
                    if consecutive_failures >= self.max_consecutive_failures:
                        task.status = TaskStatus.FAILED
                        self.agent_state.task_status = task.status
                        self.agent_state.current_node = "failed"
                        self._save_state_report(task, workflow, last_observation=last_observation)
                        print("❌ 连续失败过多，终止任务")
                        break
                    self.state_machine.transition(AgentRunState.RECOVERING)
                    strategy = self.recovery.recover(context, validation)
                    task.metrics.recovery_count += 1
                    self.agent_state.current_node = "recovering"
                    self.agent_state.total_recoveries = task.metrics.recovery_count
                    self.agent_state.consecutive_recoveries += 1
                    self.agent_stats.recovery_attempts = task.metrics.recovery_count
                    self._write_event(task, "recovery", {"round": round_index, "strategy": strategy.value, "validation": _safe_asdict(validation)})
                    if strategy == RecoveryStrategy.ABORT_TASK:
                        task.status = TaskStatus.FAILED
                        self.agent_state.task_status = task.status
                        self.agent_state.current_node = "recovery_abort"
                        self._save_state_report(task, workflow, last_observation=last_observation)
                        break
                    self.state_machine.transition(AgentRunState.OBSERVING)

            except KeyboardInterrupt:
                task.status = TaskStatus.ABORTED
                raise
            except Exception as exc:
                consecutive_failures += 1
                task.metrics.failure_count += 1
                self.agent_stats.failed_rounds += 1
                self.agent_state.current_node = "exception"
                self.agent_state.last_error = ErrorInfo(message=str(exc), context=f"round={round_index}")
                print(f"❌ Round {round_index} 异常：{exc}")
                self._write_event(task, "round_exception", {"round": round_index, "error": str(exc)})
                if consecutive_failures >= self.max_consecutive_failures:
                    task.status = TaskStatus.FAILED
                    self.agent_state.task_status = task.status
                    self.agent_state.current_node = "failed"
                    self._save_state_report(task, workflow, last_observation=last_observation)
                    break
                try:
                    self.state_machine.transition(AgentRunState.RECOVERING)
                except Exception:
                    pass
                # 重建状态机以避免异常状态转换卡住。
                self.state_machine = StateMachine()
                self.recovery.recover(
                    ExecutionContext(workflow.goal, workflow.progress, Observation(), DeviceStatus(), DeviceInfo(), self.memory, AgentRunState.RECOVERING)
                )

        task.metrics.ended_at = time.time()
        task.updated_at = datetime.now()
        self.agent_state.task_status = task.status
        self.agent_state.progress = workflow.progress
        self.agent_state.current_round = round_index
        self.agent_state.last_active_at = time.time()
        self.agent_stats.completed_objectives = len(workflow.progress.completed_objectives)
        self.agent_stats.recovery_attempts = task.metrics.recovery_count
        self.agent_stats.recovery_success_rate = self._calculate_recovery_success_rate(task)
        self._write_event(task, "task_finished", {"status": task.status.value, "duration": task.metrics.duration})
        self._save_snapshot(task, workflow, last_observation or Observation(), round_index=round_index, checkpoint=False)
        self._save_state_report(task, workflow, last_observation=last_observation)
        self._save_report(task)
        return task.status == TaskStatus.COMPLETED

    @staticmethod
    def _update_progress(progress: TaskProgress, decision: NextDecision, validation: ValidationResult) -> None:
        for item in decision.progress_update:
            if item and item not in progress.completed_objectives:
                progress.completed_objectives.append(item)
        progress.current_focus = decision.expected_outcome or decision.reason or progress.current_focus
        progress.confidence = min(1.0, progress.confidence + 0.05 if validation.passed else progress.confidence)

    def _prepare_task_resources(self, task: Task, workflow: Workflow) -> None:
        """创建符合设计方案 6.3 的任务级资源目录。

        目录结构：
        .artifacts/task_{id}/
        ├── device.json
        ├── snapshots/
        ├── logs/
        └── screenshots/
        """
        self.current_task_dir = self.artifact_root / f"task_{task.id}"
        for name in ("snapshots", "logs", "screenshots", "observations", "reports", "state"):
            (self.current_task_dir / name).mkdir(parents=True, exist_ok=True)

        # 将截图目录绑定到当前任务，避免多任务截图混在 .artifacts/screenshots。
        device = getattr(self.perception, "device", None)
        if hasattr(device, "set_artifact_dir"):
            device.set_artifact_dir(self.current_task_dir)

        device_info = _safe_asdict(device.get_info()) if device else {}
        device_payload = {
            "task_id": task.id,
            "bound_at": time.time(),
            "device_info": device_info,
            "task_goal": _safe_asdict(workflow.goal),
        }
        self._task_path("device.json").write_text(json.dumps(device_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._task_path("task.json").write_text(
            json.dumps({"task": _safe_asdict(task), "workflow": _safe_asdict(workflow)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _task_path(self, relative: str) -> Path:
        base = self.current_task_dir or self.artifact_root / "task_unknown"
        base.mkdir(parents=True, exist_ok=True)
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _write_event(self, task: Task, event: str, payload: Dict[str, Any]) -> None:
        data = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "task_id": task.id,
            "event": event,
            "payload": payload,
        }
        line = json.dumps(data, ensure_ascii=False)
        with self._task_path("logs/events.jsonl").open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _save_observation(self, task: Task, round_index: int, stage: str, observation: Observation) -> None:
        data = _compact_observation(observation)
        data["task_id"] = task.id
        data["round_index"] = round_index
        data["stage"] = stage
        data["timestamp"] = time.time()
        path = self._task_path(f"observations/round_{round_index:04d}_{stage}.json")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        # raw UI tree 可能较大，单独落盘，便于调试且避免 snapshot 过大。
        raw = observation.raw_ui_tree
        if raw is not None:
            raw_path = self._task_path(f"observations/round_{round_index:04d}_{stage}_source.xml")
            raw_path.write_text(str(raw), encoding="utf-8")

    def _save_snapshot(
        self,
        task: Task,
        workflow: Workflow,
        observation: Observation,
        round_index: int = 0,
        checkpoint: bool = False,
    ) -> None:
        data = {
            "task_id": task.id,
            "status": task.status.value,
            "current_node": workflow.current_node,
            "task_goal": _safe_asdict(workflow.goal),
            "progress": _safe_asdict(workflow.progress),
            "last_observation": _compact_observation(observation),
            "memory": {
                "page_history": self.memory.page_history,
                "action_history": self.memory.action_history,
                "failures": self.memory.failures,
                "recoveries": self.memory.recoveries,
            },
            "metrics": _safe_asdict(task.metrics),
            "agent_state": _safe_asdict(self.agent_state),
            "agent_stats": _safe_asdict(self.agent_stats),
            "health": self._diagnose_health(task),
            "round_index": round_index,
            "timestamp": time.time(),
        }
        if round_index:
            round_path = self._task_path(f"snapshots/round_{round_index:04d}.json")
            round_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if checkpoint:
            self._task_path("snapshots/checkpoint.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _calculate_recovery_success_rate(self, task: Task) -> float:
        attempts = task.metrics.recovery_count
        if attempts <= 0:
            return 1.0
        # 简化判定：最终任务完成则认为恢复链路有效；否则按非连续失败轮次估算。
        if task.status == TaskStatus.COMPLETED:
            return 1.0
        failed = max(1, task.metrics.failure_count)
        return max(0.0, min(1.0, (attempts - failed) / attempts))

    def _build_state_payload(self, task: Task, workflow: Workflow, last_observation: Optional[Observation]) -> Dict[str, Any]:
        if last_observation is not None:
            self.agent_state.last_observation = last_observation
            self.agent_state.device_status = last_observation.device_status
            self.agent_state.device_info = last_observation.device_info
        self.agent_state.task_id = task.id
        self.agent_state.task_status = task.status
        self.agent_state.task_goal = workflow.goal
        self.agent_state.progress = workflow.progress
        self.agent_state.last_decision = workflow.progress.last_decision
        self.agent_state.total_recoveries = task.metrics.recovery_count
        self.agent_state.last_active_at = time.time()
        self.agent_stats.total_actions = task.metrics.action_count
        self.agent_stats.completed_objectives = len(workflow.progress.completed_objectives)
        self.agent_stats.recovery_attempts = task.metrics.recovery_count
        self.agent_stats.recovery_success_rate = self._calculate_recovery_success_rate(task)
        return {
            "agent_state": _safe_asdict(self.agent_state),
            "agent_stats": _safe_asdict(self.agent_stats),
            "health": self._diagnose_health(task),
            "generated_at": time.time(),
            "generated_datetime": datetime.now().isoformat(),
        }

    def _diagnose_health(self, task: Task) -> Dict[str, Any]:
        issues: list[str] = []
        suggestions: list[str] = []
        uptime = task.metrics.duration
        if self.agent_state.consecutive_recoveries >= 5:
            issues.append("连续恢复次数过高，可能卡死")
            suggestions.append("建议重新观察、重新决策或重启应用")
        if uptime > 30 * 60:
            issues.append("任务运行时间超过 30 分钟")
            suggestions.append("建议检查设备状态和 Agent 活跃度")
        if task.metrics.recovery_count > 5 and self.agent_stats.recovery_success_rate < 0.5:
            issues.append("恢复成功率过低")
            suggestions.append("建议终止任务或切换恢复策略")
        idle_seconds = max(0.0, time.time() - self.agent_state.last_active_at)
        if idle_seconds > 60:
            issues.append("Agent 超过 1 分钟无活跃更新")
            suggestions.append("建议检查 Agent 是否卡住")
        return {
            "healthy": not issues,
            "issues": issues,
            "suggestions": suggestions,
            "idle_seconds": idle_seconds,
            "uptime": uptime,
        }

    def _format_state_report(self, task: Task, payload: Dict[str, Any]) -> str:
        state = payload["agent_state"]
        stats = payload["agent_stats"]
        health = payload["health"]
        total_actions = stats.get("total_actions", 0)
        successful = stats.get("successful_actions", 0)
        failed = stats.get("failed_actions", 0)
        success_rate = successful / total_actions if total_actions else 1.0
        uptime = task.metrics.duration
        completed = state.get("progress", {}).get("completed_objectives", [])
        return (
            "=== Agent 状态报告 ===\n\n"
            f"任务 ID: {state.get('task_id')}\n"
            f"任务状态: {state.get('task_status')}\n"
            f"当前轮次: {state.get('current_round')}\n"
            f"当前节点: {state.get('current_node')}\n"
            f"当前关注点: {state.get('progress', {}).get('current_focus', '')}\n"
            f"已完成目标: {completed}\n"
            f"最后页面: {(state.get('last_observation') or {}).get('page_name', 'N/A')}\n"
            f"最后决策: {(state.get('last_decision') or {}).get('type', 'N/A')} - {(state.get('last_decision') or {}).get('reason', '')}\n"
            "\n执行统计:\n"
            f"  - 总动作: {total_actions}  (成功: {successful} / 失败: {failed})\n"
            f"  - 成功率: {success_rate:.2%}\n"
            f"  - 决策轮次: {stats.get('decision_rounds', 0)}\n"
            f"  - 失败轮次: {stats.get('failed_rounds', 0)}\n"
            "\n恢复统计:\n"
            f"  - 总恢复次数: {state.get('total_recoveries', 0)}\n"
            f"  - 连续恢复: {state.get('consecutive_recoveries', 0)}\n"
            f"  - 恢复成功率: {stats.get('recovery_success_rate', 1.0):.2%}\n"
            "\n时间统计:\n"
            f"  - 运行时长: {uptime:.2f}s\n"
            f"  - LLM 调用耗时: {stats.get('llm_call_duration', 0.0):.2f}s\n"
            f"  - Device 调用耗时: {stats.get('device_call_duration', 0.0):.2f}s\n"
            "\n资源使用:\n"
            f"  - 截图次数: {stats.get('screenshot_count', 0)}\n"
            f"  - LLM Token: {stats.get('llm_token_usage', 0)}\n"
            "\n健康状态:\n"
            f"  - healthy: {health.get('healthy')}\n"
            f"  - issues: {health.get('issues')}\n"
            f"  - suggestions: {health.get('suggestions')}\n"
        )

    def _save_state_report(self, task: Task, workflow: Workflow, last_observation: Optional[Observation]) -> None:
        payload = self._build_state_payload(task, workflow, last_observation)
        self._task_path("state/stats.json").write_text(json.dumps(payload["agent_stats"], ensure_ascii=False, indent=2), encoding="utf-8")
        self._task_path("state/health.json").write_text(json.dumps(payload["health"], ensure_ascii=False, indent=2), encoding="utf-8")
        self._task_path("state/state_report.txt").write_text(self._format_state_report(task, payload), encoding="utf-8")

    def _save_report(self, task: Task) -> None:
        data = {
            "task_id": task.id,
            "goal": task.goal,
            "status": task.status.value,
            "duration": task.metrics.duration,
            "metrics": _safe_asdict(task.metrics),
            "agent_state": _safe_asdict(self.agent_state),
            "agent_stats": _safe_asdict(self.agent_stats),
            "health": self._diagnose_health(task),
            "progress": _safe_asdict(task.progress),
            "memory_summary": {
                "page_history": self.memory.page_history,
                "recent_actions": self.memory.recent_actions(20),
                "failure_count": len(self.memory.failures),
                "recovery_count": len(self.memory.recoveries),
            },
            "rounds": [
                {
                    "round_index": r.round_index,
                    "focus": r.focus,
                    "decision": _safe_asdict(r.decision),
                    "action_record": _safe_asdict(r.action_record),
                    "validation": _safe_asdict(r.validation),
                    "observation_before": _compact_observation(r.observation_before),
                    "observation_after": _compact_observation(r.observation_after),
                    "duration": r.duration,
                    "error": r.error,
                }
                for r in task.results
            ],
        }
        self._task_path("reports/report.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        # 兼容常见查找路径：任务根目录也保留一份 summary。
        self._task_path("summary.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


