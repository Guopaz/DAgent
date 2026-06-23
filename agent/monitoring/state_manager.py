"""Agent 状态管理 — 管理 AgentState 和 AgentStats。"""

from __future__ import annotations

import time
from typing import Any, Dict

from agent.models import (
    ActionRecord,
    AgentState,
    AgentStats,
    ErrorInfo,
    Plan,
    TaskStatus,
)


class StateManager:
    """状态管理器 — 管理 Agent 运行状态和统计信息。"""

    def __init__(self):
        self.state = AgentState()
        self.stats = AgentStats()

    def record_action(self, action_record: ActionRecord) -> None:
        """记录动作执行结果，更新统计信息。"""
        self.stats.total_actions += 1
        if action_record.result and action_record.result.success:
            self.stats.successful_actions += 1
        else:
            self.stats.failed_actions += 1
        
        self.stats.wda_call_duration += action_record.duration
        self.state.last_active_at = time.time()

    def record_error(self, error: ErrorInfo) -> None:
        """记录错误，更新恢复计数。"""
        self.state.last_error = error
        self.state.total_recoveries += 1
        self.state.consecutive_recoveries += 1
        self.stats.recovery_attempts += 1

    def record_recovery_success(self) -> None:
        """记录恢复成功，更新恢复成功率。"""
        self.stats.recovery_successes += 1
        self.state.consecutive_recoveries = 0

    def record_llm_call(self, duration: float, token_usage: int = 0) -> None:
        """记录 LLM 调用的耗时和 Token 用量。"""
        self.stats.llm_call_duration += duration
        self.stats.llm_token_usage += token_usage

    def record_step_completion(self, success: bool) -> None:
        """记录步骤完成。"""
        if success:
            self.stats.completed_steps += 1
        else:
            self.stats.failed_steps += 1

    def record_screenshot(self) -> None:
        """记录截图次数。"""
        self.stats.screenshot_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，用于日志和监控。"""
        uptime = time.time() - self.state.started_at if self.state.started_at else 0
        
        return {
            "task_id": self.state.task_id,
            "task_status": self.state.task_status.value,
            "current_step_index": self.state.current_step_index,
            "uptime": uptime,
            "stats": {
                "total_actions": self.stats.total_actions,
                "successful_actions": self.stats.successful_actions,
                "failed_actions": self.stats.failed_actions,
                "success_rate": self.stats.success_rate,
                "completed_steps": self.stats.completed_steps,
                "failed_steps": self.stats.failed_steps,
                "recovery_attempts": self.stats.recovery_attempts,
                "recovery_success_rate": self.stats.recovery_success_rate,
                "llm_call_duration": self.stats.llm_call_duration,
                "llm_token_usage": self.stats.llm_token_usage,
                "wda_call_duration": self.stats.wda_call_duration,
                "screenshot_count": self.stats.screenshot_count,
            },
        }

    def generate_report(self) -> str:
        """生成状态报告。"""
        data = self.to_dict()
        stats = data["stats"]
        
        report = f"""=== Agent 状态报告 ===

任务 ID: {data['task_id']}
任务状态: {data['task_status']}
当前步骤: {data['current_step_index']}

执行统计:
  - 总动作: {stats['total_actions']} (成功: {stats['successful_actions']} / 失败: {stats['failed_actions']})
  - 成功率: {stats['success_rate']:.1%}

恢复统计:
  - 总恢复次数: {stats['recovery_attempts']}
  - 连续恢复: {self.state.consecutive_recoveries}
  - 恢复成功率: {stats['recovery_success_rate']:.1%}

时间统计:
  - 运行时长: {data['uptime']:.1f}s
  - LLM 调用耗时: {stats['llm_call_duration']:.1f}s
  - WDA 调用耗时: {stats['wda_call_duration']:.1f}s

资源使用:
  - 截图次数: {stats['screenshot_count']}
  - LLM Token: {stats['llm_token_usage']}
"""
        return report
