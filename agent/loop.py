"""Agent 主循环 — Observe → Decide → Execute → Validate。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from agent.models import (
    Action,
    ActionRecord,
    ActionType,
    AgentPhase,
    Observation,
    ObservationDiff,
    Plan,
    PlanStep,
    PreCheckResult,
    RecoveryStrategy,
    StepResult,
    TaskStatus,
    UIElement,
)
from agent.monitoring.health_monitor import HealthMonitor
from agent.monitoring.state_manager import StateManager
from agent.perception.screenshot import Screenshot
from agent.perception.ui_parser import UIParser
from agent.perception.visual_analyzer import VisualAnalyzer
from agent.state.state_machine import StateMachine

if TYPE_CHECKING:
    from agent.executor.executor import Executor
    from agent.memory.memory import Memory
    from agent.planner.planner import Planner
    from agent.recovery.recovery_manager import RecoveryManager
    from agent.task.task import Task
    from agent.validator.validator import Validator
    from agent.wda.client import WDAClient
    from agent.workflow.workflow_engine import WorkflowEngine


class PerceptionLayer:
    """感知层 — 整合 UI 解析和截图采集。"""

    def __init__(self, wda: WDAClient):
        self.wda = wda
        self.ui_parser = UIParser()
        self.screenshot = Screenshot(wda)
        self.visual_analyzer = VisualAnalyzer()
        self._last_observation: Optional[Observation] = None

    def observe(self) -> Observation:
        """执行一次完整观察。"""
        # 获取 UI 树
        xml_source = ""
        elements = []
        try:
            xml_source = self.wda.get_source()
            elements = self.ui_parser.parse(xml_source)
        except Exception:
            pass

        # 获取截图
        screenshot = ""
        try:
            screenshot = self.screenshot.capture()
        except Exception:
            pass

        # 推断页面名称
        page_name = self._infer_page_name(elements)

        observation = Observation(
            elements=elements,
            screenshot_base64=screenshot,
            page_name=page_name,
            metadata={
                "xml_length": len(xml_source),
                "element_count": len(elements),
            },
        )

        self._last_observation = observation
        return observation

    def detect_changes(self, current: Observation) -> ObservationDiff:
        """检测两次观察之间的变化。"""
        if self._last_observation is None:
            return ObservationDiff()

        previous = self._last_observation

        # 比较元素
        prev_ids = {e.id for e in previous.elements}
        curr_ids = {e.id for e in current.elements}

        added = [e for e in current.elements if e.id in (curr_ids - prev_ids)]
        removed = [e for e in previous.elements if e.id in (prev_ids - curr_ids)]

        # 检测变化的元素
        changed = []
        common_ids = prev_ids & curr_ids
        prev_map = {e.id: e for e in previous.elements}
        curr_map = {e.id: e for e in current.elements}
        for eid in common_ids:
            prev_e = prev_map[eid]
            curr_e = curr_map[eid]
            if (prev_e.text != curr_e.text or
                prev_e.value != curr_e.value or
                prev_e.visible != curr_e.visible or
                prev_e.enabled != curr_e.enabled):
                changed.append(curr_e)

        # 检测弹窗、键盘、加载状态
        has_alert = any(e.type.value == "alert" for e in current.elements)
        has_keyboard = any(e.type.value == "keyboard" for e in current.elements)
        is_loading = self._detect_loading(current)

        # 计算相似度
        total = max(len(prev_ids | curr_ids), 1)
        changed_count = len(added) + len(removed) + len(changed)
        similarity = 1.0 - (changed_count / total)

        return ObservationDiff(
            added=added,
            removed=removed,
            changed=changed,
            page_changed=similarity < 0.7,
            has_alert=has_alert,
            has_keyboard=has_keyboard,
            is_loading=is_loading,
            similarity=similarity,
        )

    def _infer_page_name(self, elements: list[UIElement]) -> str:
        """从元素推断页面名称。"""
        for e in elements:
            if e.type.value in ("navigation_bar",):
                return e.text or e.label or "导航页"
        return "未知页面"

    def _detect_loading(self, observation: Observation) -> bool:
        """检测加载状态。"""
        loading_keywords = ["loading", "加载中", "请稍候", "progress", "加载中"]
        for e in observation.elements:
            text = (e.text or "").lower()
            if any(kw in text for kw in loading_keywords):
                return True
        return False


class AgentLoop:
    """Agent 主循环 — 协调各模块完成任务。"""

    def __init__(
        self,
        wda: WDAClient,
        perception: PerceptionLayer,
        planner: Planner,
        executor: Executor,
        validator: Validator,
        recovery: RecoveryManager,
        memory: Memory,
        workflow_engine: Optional[WorkflowEngine] = None,
        max_actions_per_step: int = 10,
        max_consecutive_failures: int = 5,
    ):
        self.wda = wda
        self.perception = perception
        self.planner = planner
        self.executor = executor
        self.validator = validator
        self.recovery = recovery
        self.memory = memory
        self.workflow_engine = workflow_engine
        self.max_actions_per_step = max_actions_per_step
        self.max_consecutive_failures = max_consecutive_failures

        self.state_machine = StateMachine()
        self.state_manager = StateManager()
        self.health_monitor = HealthMonitor(self.state_manager)

    def run_task(self, task: Task) -> bool:
        """运行任务，返回是否成功。"""
        print(f"🎯 开始执行任务: {task.goal}")
        
        # 初始化
        self._init_task(task)

        # 生成执行计划
        plan = self._generate_plan(task)
        if not plan or not plan.steps:
            print("❌ 无法生成执行计划")
            task.fail("无法生成执行计划")
            return False

        task.plan = plan
        print(f"📋 执行计划 ({len(plan.steps)} 步):")
        for step in plan.steps:
            print(f"  {step.index}. {step.description}")

        # 执行每个步骤
        all_success = True
        for step_index, step in enumerate(plan.steps):
            print(f"\n{'='*60}")
            print(f"步骤 {step.index}/{len(plan.steps)}: {step.description}")
            print(f"{'='*60}")

            success = self._execute_step(task, step)
            
            result = StepResult(
                step_index=step.index,
                success=success,
                message="成功" if success else "失败",
                actions_count=len(step.actions),
            )
            task.results.append(result)

            if not success:
                all_success = False
                print(f"❌ 步骤失败: {step.description}")
                
                # 检查是否需要终止
                if self.state_manager.state.consecutive_recoveries >= self.max_consecutive_failures:
                    print("❌ 连续失败过多，终止任务")
                    task.fail("连续失败过多")
                    break
            else:
                print(f"✅ 步骤完成: {step.description}")
                self.state_manager.state.consecutive_recoveries = 0

            # 保存快照
            self.state_manager.record_step_completion(success)

        # 完成任务
        if all_success:
            task.complete()
            print(f"\n🎉 任务完成: {task.goal}")
        else:
            completed = sum(1 for r in task.results if r.success)
            if completed > 0:
                task.status = TaskStatus.PARTIAL
                print(f"\n⚠️ 任务部分完成: {completed}/{len(plan.steps)} 步骤成功")
            else:
                task.fail("所有步骤失败")
                print(f"\n❌ 任务失败: {task.goal}")

        # 生成最终报告
        print(self.state_manager.generate_report())

        return all_success

    def _init_task(self, task: Task) -> None:
        """初始化任务状态。"""
        task.start()
        self.state_manager.state.task_id = task.task_id
        self.state_manager.state.task_status = TaskStatus.RUNNING
        self.state_machine.force_transition(AgentPhase.INIT)
        self.memory.clear()

    def _generate_plan(self, task: Task) -> Optional[Plan]:
        """生成执行计划。"""
        if self.workflow_engine:
            workflow = self.workflow_engine.create_workflow(task)
            return workflow.plan
        
        # 降级：创建单步计划
        return Plan(
            steps=[PlanStep(index=1, description=task.goal, status="pending")],
            raw_text=task.goal,
        )

    def _execute_step(self, task: Task, step: PlanStep) -> bool:
        """执行单个步骤。"""
        step.status = "running"
        action_count = 0
        consecutive_failures = 0

        while action_count < self.max_actions_per_step:
            # 前置检查
            pre_check = self._pre_check()
            if pre_check == PreCheckResult.HANDLED:
                print("  🔧 已处理干扰因素，重新观察")
                continue
            if pre_check == PreCheckResult.WAIT:
                print("  ⏳ 等待加载完成")
                time.sleep(2)
                continue
            if pre_check == PreCheckResult.ABORT:
                print("  ❌ 前置检查失败")
                return False

            # 观察
            self.state_machine.force_transition(AgentPhase.OBSERVING)
            observation = self.perception.observe()
            self.memory.record_observation(observation)
            self.state_manager.record_screenshot()

            # 决策
            self.state_machine.force_transition(AgentPhase.PLANNING)
            action_history = self.memory.get_action_history_text(5)
            
            start_time = time.time()
            action = self.planner.plan(step.description, observation, action_history)
            llm_duration = time.time() - start_time
            self.state_manager.record_llm_call(llm_duration)

            print(f"  💡 决策: {action.action_type.value} - {action.reason}")

            # 无操作表示步骤完成
            if action.action_type == ActionType.NONE:
                print("  ✅ Planner 认为步骤已完成")
                step.status = "success"
                return True

            # 执行
            self.state_machine.force_transition(AgentPhase.EXECUTING)
            record = self.executor.execute(action)
            self.memory.record_action(record)
            self.state_manager.record_action(record)

            action_count += 1

            if not record.result or not record.result.success:
                print(f"  ❌ 执行失败: {record.result.message if record.result else '未知错误'}")
                consecutive_failures += 1
                
                # 恢复
                error = self.recovery.classify_error(
                    Exception(record.result.message if record.result else "执行失败"),
                    context=step.description,
                )
                self.state_manager.record_error(error)
                
                strategy = self.recovery.handle_error(error, consecutive_failures)
                print(f"  🔄 恢复策略: {strategy.value}")
                
                if strategy == RecoveryStrategy.ABORT_TASK:
                    step.status = "failed"
                    return False
                if strategy == RecoveryStrategy.SKIP_STEP:
                    step.status = "skipped"
                    return True
                
                continue
            
            print(f"  ✅ 执行成功: {record.result.message}")
            consecutive_failures = 0

            # 验证
            self.state_machine.force_transition(AgentPhase.VALIDATING)
            time.sleep(1)
            
            new_observation = self.perception.observe()
            validation = self.validator.validate_step_completion(
                new_observation,
                step.description,
            )

            if validation.passed:
                print(f"  ✅ 验证通过: {validation.reason}")
                step.status = "success"
                return True

            print(f"  ⚠️ 验证未通过: {validation.reason}，继续执行")

        # 超过最大动作数
        print(f"  ⚠️ 超过最大动作数 ({self.max_actions_per_step})")
        step.status = "failed"
        return False

    def _pre_check(self) -> PreCheckResult:
        """前置检查 — 处理弹窗、键盘、加载状态。"""
        try:
            observation = self.perception.observe()
            
            # 检查弹窗
            has_alert = any(e.type.value == "alert" for e in observation.elements)
            if has_alert:
                print("  🔔 检测到弹窗，尝试关闭")
                try:
                    self.wda.dismiss_alert()
                    time.sleep(1)
                    return PreCheckResult.HANDLED
                except Exception:
                    pass

            # 检查键盘
            has_keyboard = any(e.type.value == "keyboard" for e in observation.elements)
            if has_keyboard:
                print("  ⌨️ 检测到键盘，尝试关闭")
                try:
                    self.wda.dismiss_keyboard()
                    time.sleep(0.5)
                    return PreCheckResult.HANDLED
                except Exception:
                    pass

            # 检查加载状态
            is_loading = self.perception._detect_loading(observation)
            if is_loading:
                return PreCheckResult.WAIT

            return PreCheckResult.NORMAL
        except Exception:
            return PreCheckResult.ABORT
