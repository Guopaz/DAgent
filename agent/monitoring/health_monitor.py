"""健康监控 — 实时检测 Agent 运行健康状态。"""

from __future__ import annotations

import time
from typing import List, TYPE_CHECKING

from agent.models import HealthCheck

if TYPE_CHECKING:
    from agent.monitoring.state_manager import StateManager


class HealthMonitor:
    """健康监控器 — 检查 Agent 运行状态。"""

    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager

    def check_health(self) -> List[HealthCheck]:
        """执行健康检查，返回检查结果列表。"""
        checks = []
        
        # 检查连续恢复次数
        checks.append(self._check_consecutive_recoveries())
        
        # 检查任务运行时长
        checks.append(self._check_uptime())
        
        # 检查恢复成功率
        checks.append(self._check_recovery_rate())
        
        # 检查空闲时间
        checks.append(self._check_idle_time())
        
        return checks

    def _check_consecutive_recoveries(self) -> HealthCheck:
        """检查连续恢复次数。"""
        count = self.state_manager.state.consecutive_recoveries
        threshold = 5
        
        return HealthCheck(
            name="连续恢复次数",
            healthy=count < threshold,
            message=f"连续恢复 {count} 次" if count >= threshold else "正常",
            value=count,
            threshold=threshold,
        )

    def _check_uptime(self) -> HealthCheck:
        """检查任务运行时长。"""
        uptime = time.time() - self.state_manager.state.started_at if self.state_manager.state.started_at else 0
        threshold = 30 * 60  # 30 分钟
        
        return HealthCheck(
            name="任务运行时长",
            healthy=uptime < threshold,
            message=f"运行 {uptime/60:.1f} 分钟，可能过长" if uptime >= threshold else "正常",
            value=uptime,
            threshold=threshold,
        )

    def _check_recovery_rate(self) -> HealthCheck:
        """检查恢复成功率。"""
        rate = self.state_manager.stats.recovery_success_rate
        attempts = self.state_manager.stats.recovery_attempts
        threshold = 0.5
        
        healthy = rate >= threshold or attempts <= 5
        
        return HealthCheck(
            name="恢复成功率",
            healthy=healthy,
            message=f"恢复成功率 {rate:.1%}，效果差" if not healthy else "正常",
            value=rate,
            threshold=threshold,
        )

    def _check_idle_time(self) -> HealthCheck:
        """检查空闲时间。"""
        idle_time = time.time() - self.state_manager.state.last_active_at if self.state_manager.state.last_active_at else 0
        threshold = 60  # 1 分钟
        
        return HealthCheck(
            name="空闲时间",
            healthy=idle_time < threshold,
            message=f"空闲 {idle_time:.1f} 秒，可能卡死" if idle_time >= threshold else "正常",
            value=idle_time,
            threshold=threshold,
        )

    def is_healthy(self) -> bool:
        """检查 Agent 是否健康。"""
        checks = self.check_health()
        return all(c.healthy for c in checks)

    def get_unhealthy_checks(self) -> List[HealthCheck]:
        """获取不健康的检查项。"""
        checks = self.check_health()
        return [c for c in checks if not c.healthy]
