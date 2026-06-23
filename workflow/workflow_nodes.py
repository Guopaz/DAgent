"""工作流节点 — 所有 Routine / Reasoning / Checkpoint / Action 节点实现

节点按类型分为四类：
- Routine:    例行节点，确定性逻辑，无需 LLM
- Reasoning:  推理节点，需要 LLM 推理和判断
- Checkpoint: 检查点节点，条件判断，决定流程走向
- Action:     执行节点，执行具体工具调用
"""

import json
from typing import Any, Dict, List, Optional

from .workflow_engine import (
    NodeResult,
    RoutineResult,
    ReasoningResult,
    CheckpointResult,
    ActionResult,
)


# =========================================================================
# Tool Filter (per-step)
# =========================================================================

class StepToolFilter:
    """按步骤过滤可用工具，减少 LLM 选择范围

    规则：
    1. tools_hint 中指定的工具始终可用
    2. ALWAYS_AVAILABLE 中的工具始终可用（wda_call 是万能后备）
    3. 如果 tools_hint 为空，返回全部工具（不过滤）
    """

    ALWAYS_AVAILABLE = {"wda_call", "observe_screen", "inspect_element"}

    def __init__(self, tool_registry):
        self.tool_registry = tool_registry

    def filter_for_step(self, step: Optional[dict]) -> list:
        """根据步骤的 tools_hint 返回过滤后的工具 schema 列表"""
        if not step:
            return self._all_schemas()

        hints = step.get("tools_hint", [])
        if not hints:
            return self._all_schemas()

        allowed = set(hints) | self.ALWAYS_AVAILABLE
        all_schemas = self._all_schemas()
        filtered = [
            s for s in all_schemas
            if s.get("function", {}).get("name", "") in allowed
        ]
        return filtered if filtered else all_schemas

    def _all_schemas(self) -> list:
        """获取所有工具 schema"""
        if self.tool_registry is None:
            return []
        return self.tool_registry.get_tool_schemas()


# =========================================================================
# Routine: 环境初始化
# =========================================================================

class InitRoutine:
    """环境初始化：重置屏幕监听器，获取初始屏幕状态

    迁移自：iOSAgent._on_loop_start（screen_monitor.reset + refresh）
    """

    def execute(self, device_ctx) -> RoutineResult:
        device_ctx.screen_monitor.reset()
        device_ctx.screen_monitor.refresh()
        return RoutineResult(status="success", data={
            "initial_screen": device_ctx.screen_monitor.get_summary()
        })


# =========================================================================
# Routine: 前置清理
# =========================================================================

class CleanupRoutine:
    """前置清理：自动处理弹窗和键盘

    新增节点：将弹窗/键盘处理从 LLM 判断改为确定性前置处理。
    """

    def execute(self, device_ctx) -> RoutineResult:
        results = []

        # 1. 检测并关闭系统弹窗（Alert）
        alert_info = device_ctx.screen_monitor.detect_alert()
        if alert_info:
            try:
                device_ctx.wda.accept_alert()
                results.append(f"已处理弹窗: {alert_info.get('title', '未知')}")
                device_ctx.screen_monitor.refresh()
            except Exception as e:
                results.append(f"弹窗处理失败: {e}")

        # 2. 检测并收起键盘
        if device_ctx.screen_monitor.detect_keyboard():
            try:
                device_ctx.wda.dismiss_keyboard()
                results.append("已收起键盘")
                device_ctx.screen_monitor.refresh()
            except Exception as e:
                results.append(f"键盘收起失败: {e}")

        return RoutineResult(status="success", data={"cleanup_actions": results})


# =========================================================================
# Reasoning: 任务规划
# =========================================================================

class PlanReasoning:
    """任务规划：将用户任务分解为结构化的操作计划

    不复用 PlanSolveAgent，专为设备操作场景设计。
    """

    PLAN_SCHEMA = {
        "type": "function",
        "function": {
            "name": "generate_plan",
            "description": "为 iOS 自动化任务生成操作计划",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {
                        "type": "string",
                        "description": "任务目标的一句话描述"
                    },
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {
                                    "type": "integer",
                                    "description": "步骤编号"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "步骤描述"
                                },
                                "expected_screen": {
                                    "type": "string",
                                    "description": "执行后预期的屏幕状态"
                                },
                                "tools_hint": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "建议使用的工具列表"
                                },
                                "max_retries": {
                                    "type": "integer",
                                    "description": "最大重试次数",
                                    "default": 3,
                                },
                            },
                            "required": ["id", "description", "expected_screen"],
                        },
                    },
                },
                "required": ["goal", "steps"],
            },
        },
    }

    def execute(self, llm_ctx, device_ctx, task_ctx) -> ReasoningResult:
        current_screen = device_ctx.screen_monitor.get_summary()

        # 获取可用工具名称列表
        if task_ctx.tool_registry:
            available_tools = task_ctx.tool_registry.list_tools()
        else:
            available_tools = []

        prompt = (
            "你是一个 iOS 设备自动化规划专家。\n\n"
            f"## 当前屏幕状态\n{current_screen}\n\n"
            f"## 可用工具\n{', '.join(available_tools)}\n\n"
            f"## 任务\n{task_ctx.task}\n\n"
            "请生成一个操作计划。每个步骤必须是可通过一次工具调用完成的原子操作。\n"
            "expected_screen 用于后续验证操作是否成功。\n"
            "步骤数量控制在 3-10 步之间，不要过于细化。"
        )

        messages = [{"role": "user", "content": prompt}]
        response = llm_ctx.llm.invoke_with_tools(
            messages=messages,
            tools=[self.PLAN_SCHEMA],
            tool_choice="auto",
        )

        task_ctx.increment_llm_call(
            tokens=response.usage.get("total_tokens", 0)
        )

        # 解析工具调用或文本响应
        plan = None
        if response.tool_calls:
            for tool_call in response.tool_calls:
                if tool_call.name == "generate_plan":
                    try:
                        plan = json.loads(tool_call.arguments)
                        break
                    except (json.JSONDecodeError, ValueError) as e:
                        print(f"⚠️ 工具参数 JSON 解析失败: {e}")
                        print(f"   原始参数: {tool_call.arguments[:200]}")
                        # 继续尝试其他工具调用或降级处理
                        continue
        
        if plan is None:
            # 如果模型没有调用工具，尝试从文本响应中解析 JSON
            try:
                # 尝试从文本中提取 JSON
                json_match = re.search(r'\{[\s\S]*"goal"[\s\S]*"steps"[\s\S]*\}', response.content)
                if json_match:
                    plan = json.loads(json_match.group())
            except (json.JSONDecodeError, AttributeError):
                pass
        
        if plan is None:
            plan = {"goal": task_ctx.task, "steps": []}

        task_ctx.plan = plan
        task_ctx.current_step_index = 0

        print(f"📋 计划已生成: {len(plan.get('steps', []))} 个步骤")
        for step in plan.get("steps", []):
            print(f"   {step['id']}. {step['description']}")

        return ReasoningResult(status="success", data=plan)


# =========================================================================
# Routine: 屏幕刷新
# =========================================================================

class RefreshRoutine:
    """屏幕刷新：获取最新屏幕状态并注入到消息上下文

    迁移自：_after_tool_execution 中的屏幕刷新 + _before_llm_call 中的状态注入
    """

    def execute(self, device_ctx, llm_ctx) -> RoutineResult:
        device_ctx.screen_monitor.refresh()

        # 注入到消息上下文
        if llm_ctx.context_manager:
            llm_ctx.context_manager.inject_screen_state(
                llm_ctx.messages, device_ctx.screen_monitor
            )

        return RoutineResult(status="success", data={
            "snapshot_count": device_ctx.screen_monitor._snapshot_count,
            "screen_changed": device_ctx.screen_monitor.has_changed(),
        })


# =========================================================================
# Routine: 前置检查
# =========================================================================

class PreCheckRoutine:
    """前置检查：每步操作前确保没有阻塞状态

    新增节点：将弹窗/键盘检测从 LLM 判断改为确定性前置处理。
    """

    def execute(self, device_ctx, task_ctx) -> RoutineResult:
        actions_taken = []

        # 1. 检测弹窗
        alert = device_ctx.screen_monitor.detect_alert()
        if alert:
            try:
                alert_type = alert.get("type", "system")
                if alert_type == "permission":
                    device_ctx.wda.accept_alert()
                    actions_taken.append(f"已允许权限: {alert.get('title', '')}")
                else:
                    device_ctx.wda.dismiss_alert()
                    actions_taken.append(f"已关闭弹窗: {alert.get('title', '')}")
                device_ctx.screen_monitor.refresh()
            except Exception as e:
                actions_taken.append(f"弹窗处理失败: {e}")

        # 2. 检测键盘
        if device_ctx.screen_monitor.detect_keyboard():
            current_step = task_ctx.get_current_step()
            needs_input = current_step and any(
                "input" in t for t in current_step.get("tools_hint", [])
            )
            if not needs_input:
                try:
                    device_ctx.wda.dismiss_keyboard()
                    actions_taken.append("键盘已自动收起（当前步骤无需输入）")
                    device_ctx.screen_monitor.refresh()
                except Exception as e:
                    actions_taken.append(f"键盘收起失败: {e}")
            else:
                actions_taken.append("键盘可见，当前步骤需要输入，保留")

        # 3. 检测加载状态
        if device_ctx.screen_monitor.is_loading():
            device_ctx.screen_monitor.refresh()
            actions_taken.append("等待加载完成")

        if actions_taken:
            for action in actions_taken:
                print(f"  🔍 前置检查: {action}")

        return RoutineResult(status="success", data={
            "actions_taken": actions_taken,
            "screen_ready": True,
        })


# =========================================================================
# Reasoning: 步骤决策
# =========================================================================

class DecideReasoning:
    """步骤决策：决定本步执行什么操作

    根据当前屏幕状态和计划，决定本步操作。
    支持操作批处理：LLM 在一次响应中返回多个 tool_calls。
    """

    def __init__(self, tool_filter: Optional[StepToolFilter] = None):
        self.tool_filter = tool_filter

    def execute(self, llm_ctx, task_ctx, device_ctx) -> ReasoningResult:
        current_step = task_ctx.get_current_step()
        current_screen = device_ctx.screen_monitor.get_summary()

        # 过滤工具
        if self.tool_filter:
            available_tools = self.tool_filter.filter_for_step(current_step)
        elif task_ctx.tool_filter:
            available_tools = task_ctx.tool_filter.filter_for_step(current_step)
        else:
            available_tools = task_ctx.tool_registry.get_tool_schemas() if task_ctx.tool_registry else []

        step_desc = ""
        if current_step:
            step_desc = f"步骤 {current_step.get('id', '?')}: {current_step.get('description', '?')}"
        else:
            step_desc = "（无当前步骤信息，请根据任务目标自行判断）"

        prompt = (
            f"## 当前任务\n{task_ctx.task}\n\n"
            f"## 操作计划\n{task_ctx.format_plan_progress()}\n\n"
            f"## 当前步骤\n{step_desc}\n\n"
            f"## 当前屏幕\n{current_screen}\n\n"
            "请决定本步的具体操作。如果计划中的步骤在当前屏幕上无法执行，"
            "请说明原因并调整操作策略。\n"
            "如果当前步骤已完成，可以执行下一步操作。"
        )

        messages = llm_ctx.messages + [{"role": "user", "content": prompt}]
        response = llm_ctx.llm.invoke_with_tools(
            messages=messages,
            tools=available_tools,
        )

        task_ctx.increment_llm_call(
            tokens=response.usage.get("total_tokens", 0)
        )

        # 记录推理过程
        if response.content:
            print(f"💭 推理: {response.content}")

        # 提取 LLM 选择的工具和参数（支持批量操作）
        if response.tool_calls:
            operations = []
            for tc in response.tool_calls:
                try:
                    args = json.loads(tc.arguments) if isinstance(tc.arguments, str) else tc.arguments
                except json.JSONDecodeError:
                    args = {}
                operations.append({
                    "tool_name": tc.name,
                    "arguments": args,
                })
                print(f"🔧 操作: {tc.name}({args})")

            task_ctx.current_operation = operations
            return ReasoningResult(status="success", data={
                "operations": operations,
                "reasoning": response.content,
            })

        return ReasoningResult(status="no_action", data={
            "reasoning": response.content or "LLM 未返回工具调用"
        })


# =========================================================================
# Action: 执行操作
# =========================================================================

class ExecuteAction:
    """执行操作：调用工具注册表执行具体操作

    支持批量执行：当 DecideReasoning 返回多个操作时，按序执行。
    """

    def execute(self, task_ctx, device_ctx) -> ActionResult:
        operations = task_ctx.current_operation
        if not operations:
            return ActionResult(status="executed", data={"results": []})

        tool_calls = operations if isinstance(operations, list) else [operations]
        results = []

        for call in tool_calls:
            tool_name = call["tool_name"]
            arguments = call.get("arguments", {})

            try:
                tool = task_ctx.tool_registry.get_tool(tool_name)
                if tool is None:
                    result_text = f"❌ 工具 {tool_name} 不存在"
                    success = False
                else:
                    # Tool.run 接收 parameters dict
                    tool_response = tool.run(arguments)
                    result_text = tool_response.text if hasattr(tool_response, 'text') else str(tool_response)
                    success = not (hasattr(tool_response, 'status') and tool_response.status == "error")
                    print(f"👀 观察: {result_text[:200]}")
            except Exception as e:
                result_text = f"❌ 工具执行失败: {e}"
                success = False
                print(result_text)

            results.append({
                "tool_name": tool_name,
                "arguments": arguments,
                "success": success,
                "output": result_text,
            })

            # 动作工具执行后刷新屏幕
            from .workflow_tool_helpers import is_action_tool
            if is_action_tool(tool_name, arguments):
                try:
                    device_ctx.screen_monitor.refresh()
                    print(f"📱 屏幕已刷新 (第{device_ctx.screen_monitor._snapshot_count}帧)")
                except Exception as e:
                    device_ctx.screen_monitor.mark_stale()
                    print(f"⚠️ 屏幕自动刷新失败: {e}")

        task_ctx.step_results = results
        task_ctx.all_step_results.extend(results)
        return ActionResult(status="executed", data={"results": results})


# =========================================================================
# Checkpoint: 结果验证
# =========================================================================

class VerifyCheckpoint:
    """结果验证：优先确定性验证，必要时才调用 LLM

    验证策略：
    1. 确定性验证：基于屏幕 diff、元素存在性等客观条件
    2. 预期屏幕验证：轻量 LLM 语义对比
    3. 全部完成判断
    """

    DETERMINISTIC_CHECKS = {
        "tap_element":              "check_element_disappeared_or_page_changed",
        "input_text":               "check_input_field_has_value",
        "go_back":                  "check_page_changed",
        "scroll_to_find_and_tap":   "check_element_tapped_or_page_changed",
        "handle_alert":             "check_alert_dismissed",
        "restart_app":              "check_app_relaunched",
    }

    def execute(self, task_ctx, device_ctx, llm_ctx) -> CheckpointResult:
        current_step = task_ctx.get_current_step()
        step_results = task_ctx.step_results

        # ---- 阶段 1：工具执行结果检查 ----
        for result in step_results:
            if not result.get("success", False):
                task_ctx.last_failure_reason = f"工具执行失败: {result.get('output', '')}"
                return CheckpointResult(
                    status="failed",
                    data={"reason": task_ctx.last_failure_reason},
                )

        # ---- 阶段 2：确定性验证 ----
        for result in step_results:
            tool_name = result["tool_name"]
            check_method = self.DETERMINISTIC_CHECKS.get(tool_name)
            if check_method:
                passed = self._deterministic_check(check_method, device_ctx, result)
                if not passed:
                    task_ctx.last_failure_reason = f"确定性验证未通过: {check_method}"
                    return CheckpointResult(
                        status="failed",
                        data={"reason": task_ctx.last_failure_reason},
                    )

        # ---- 阶段 3：预期屏幕验证（轻量 LLM 调用）----
        expected_screen = current_step.get("expected_screen") if current_step else None
        if expected_screen:
            current_screen = device_ctx.screen_monitor.get_summary()
            match = self._semantic_check(llm_ctx, expected_screen, current_screen, task_ctx)
            if not match:
                task_ctx.last_failure_reason = "当前屏幕与预期不匹配"
                return CheckpointResult(
                    status="failed",
                    data={"reason": task_ctx.last_failure_reason},
                )

        # 验证通过，重置连续恢复计数
        task_ctx.reset_consecutive_recoveries()

        # ---- 判断是否全部完成 ----
        if task_ctx.is_all_steps_completed():
            task_ctx.status = "completed"
            return CheckpointResult(status="completed")

        # 推进到下一步
        task_ctx.advance_step()
        current = task_ctx.get_current_step()
        if current:
            print(f"  ➡️ 进入步骤 {current.get('id', '?')}: {current.get('description', '?')}")
        return CheckpointResult(status="passed")

    def _deterministic_check(self, method: str, device_ctx, result: dict) -> bool:
        """确定性验证：基于屏幕 diff、元素存在性等客观条件判断"""
        screen = device_ctx.screen_monitor
        if method == "check_page_changed":
            return screen.has_changed()
        elif method == "check_alert_dismissed":
            return not screen.detect_alert()
        elif method == "check_element_disappeared_or_page_changed":
            return screen.has_changed()
        elif method == "check_element_tapped_or_page_changed":
            return screen.has_changed()
        elif method == "check_input_field_has_value":
            return True  # 输入操作通常可靠
        elif method == "check_app_relaunched":
            return True  # 重启操作通常可靠
        return True

    def _semantic_check(self, llm_ctx, expected: str, current: str, task_ctx) -> bool:
        """语义验证：使用轻量 LLM 调用对比预期与实际屏幕"""
        prompt = (
            "你是一个 iOS 自动化验证专家。请判断当前屏幕状态是否与预期大致匹配。\n\n"
            f"## 预期屏幕\n{expected}\n\n"
            f"## 当前屏幕\n{current}\n\n"
            "只需回答 'yes' 或 'no'，不需要详细解释。"
        )
        try:
            response = llm_ctx.llm.invoke(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            task_ctx.increment_llm_call(
                tokens=response.usage.get("total_tokens", 0)
            )
            answer = response.content.strip().lower()
            return "yes" in answer
        except Exception:
            return True  # LLM 验证失败时，默认通过


# =========================================================================
# Reasoning: 错误恢复
# =========================================================================

class RecoveryReasoning:
    """错误恢复：分析失败原因并决定恢复策略

    带硬性护栏：
    - 单步骤最多重试 3 次
    - 全局恢复次数上限 10 次
    - 连续 3 步进入恢复 → 触发计划重评估
    """

    MAX_RETRIES_PER_STEP = 3
    MAX_TOTAL_RECOVERIES = 10
    REPLAN_THRESHOLD = 3  # 连续恢复次数触发重评估

    def execute(self, llm_ctx, task_ctx, device_ctx) -> ReasoningResult:
        current_step = task_ctx.get_current_step()
        retry_count = task_ctx.consecutive_recoveries

        # 刷新屏幕（失败后屏幕可能已变化）
        device_ctx.screen_monitor.refresh()

        # ---- 硬性护栏检查 ----
        if retry_count >= self.MAX_RETRIES_PER_STEP:
            print(f"  ⚠️ 步骤已重试 {retry_count} 次，强制跳过")
            if current_step:
                task_ctx.advance_step()
            task_ctx.reset_consecutive_recoveries()
            if task_ctx.is_all_steps_completed():
                task_ctx.status = "partial"
                return ReasoningResult(status="abort", data={
                    "reason": "所有步骤均已完成或跳过"
                })
            return ReasoningResult(status="skip", data={
                "reason": f"步骤已重试 {retry_count} 次，强制跳过"
            })

        if task_ctx.total_recoveries >= self.MAX_TOTAL_RECOVERIES:
            task_ctx.status = "aborted"
            return ReasoningResult(status="abort", data={
                "reason": f"全局恢复次数已达上限 ({self.MAX_TOTAL_RECOVERIES})，终止任务"
            })

        # ---- 计划重评估 ----
        if task_ctx.consecutive_recoveries >= self.REPLAN_THRESHOLD:
            print("  🔄 连续恢复次数过多，触发计划重评估")
            return self._replan(llm_ctx, task_ctx, device_ctx)

        # ---- LLM 分析失败原因并决定策略 ----
        current_screen = device_ctx.screen_monitor.get_summary()
        step_results = task_ctx.step_results

        prompt = (
            "## 操作失败分析\n\n"
            f"任务：{task_ctx.task}\n"
            f"当前步骤：{current_step.get('description', '?') if current_step else '?'}\n"
            f"失败原因：{task_ctx.last_failure_reason}\n"
            f"当前屏幕：{current_screen}\n"
            f"操作结果：{json.dumps(step_results[-2:], ensure_ascii=False) if step_results else '无'}\n"
            f"已重试次数：{retry_count}/{self.MAX_RETRIES_PER_STEP}\n\n"
            "请选择恢复策略：\n"
            "1. retry：换一种方式重试当前步骤（必须说明换什么方式）\n"
            "2. skip：跳过当前步骤，继续下一步\n"
            "3. abort：任务无法完成，终止执行"
        )

        recovery_schema = {
            "type": "function",
            "function": {
                "name": "decide_recovery",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["retry", "skip", "abort"],
                        },
                        "reason": {"type": "string"},
                        "alternative_approach": {
                            "type": "string",
                            "description": "如果选择 retry，说明替代方案",
                        },
                    },
                    "required": ["action", "reason"],
                },
            },
        }

        response = llm_ctx.llm.invoke_with_tools(
            messages=[{"role": "user", "content": prompt}],
            tools=[recovery_schema],
            tool_choice="auto",
        )

        task_ctx.increment_llm_call(
            tokens=response.usage.get("total_tokens", 0)
        )

        if response.tool_calls:
            decision = json.loads(response.tool_calls[0].arguments)
        else:
            decision = {"action": "retry", "reason": response.content or "默认重试"}

        task_ctx.increment_recovery_count()
        action = decision.get("action", "retry")
        print(f"  🔧 恢复策略: {action} — {decision.get('reason', '')}")

        if action == "skip":
            if current_step:
                task_ctx.advance_step()
            task_ctx.reset_consecutive_recoveries()
            if task_ctx.is_all_steps_completed():
                task_ctx.status = "partial"
                return ReasoningResult(status="abort", data=decision)

        if action == "abort":
            task_ctx.status = "aborted"

        return ReasoningResult(status=action, data=decision)

    def _replan(self, llm_ctx, task_ctx, device_ctx) -> ReasoningResult:
        """触发计划重评估：调用 PlanReasoning 重新生成剩余步骤"""
        planner = PlanReasoning()
        current_screen = device_ctx.screen_monitor.get_summary()

        remaining = "（需要重新规划）"
        if task_ctx.plan:
            remaining_steps = task_ctx.plan.get("steps", [])[task_ctx.current_step_index:]
            remaining = json.dumps(remaining_steps, ensure_ascii=False)

        original_task = task_ctx.task
        task_ctx.task = (
            f"[重评估] 原任务: {original_task}\n"
            f"当前屏幕: {current_screen}\n"
            f"未完成步骤: {remaining}\n"
            f"请基于当前屏幕状态重新生成剩余步骤的计划。"
        )

        result = planner.execute(llm_ctx, device_ctx, task_ctx)
        task_ctx.task = original_task
        task_ctx.reset_consecutive_recoveries()

        return ReasoningResult(status="retry", data={
            "action": "retry",
            "reason": "已重新规划，重试新计划的第一步",
            "replanned": True,
        })


# =========================================================================
# Routine: 任务总结
# =========================================================================

class SummaryRoutine:
    """任务总结：生成结构化的执行报告"""

    def execute(self, task_ctx) -> RoutineResult:
        total_steps = len(task_ctx.plan.get("steps", [])) if task_ctx.plan else 0

        report = {
            "task": task_ctx.task,
            "status": task_ctx.status,
            "total_steps": total_steps,
            "completed_steps": task_ctx.current_step_index,
            "total_llm_calls": task_ctx.stats.get("llm_calls", 0),
            "total_tokens": task_ctx.stats.get("total_tokens", 0),
            "total_recoveries": task_ctx.total_recoveries,
            "duration_seconds": round(task_ctx.elapsed_seconds(), 1),
        }

        summary_lines = [
            f"{'='*50}",
            f"📊 任务执行报告",
            f"{'='*50}",
            f"任务：{task_ctx.task}",
            f"状态：{report['status']}",
            f"完成步骤：{report['completed_steps']}/{report['total_steps']}",
            f"LLM 调用：{report['total_llm_calls']} 次，Token：{report['total_tokens']}",
            f"恢复次数：{report['total_recoveries']}",
            f"耗时：{report['duration_seconds']}s",
        ]

        summary = "\n".join(summary_lines)
        task_ctx.summary = summary

        print(summary)

        # 清理状态文件
        task_ctx.clean_state()

        return RoutineResult(status="success", data={
            "report": report,
            "summary": summary,
        })
