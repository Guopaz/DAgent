"""恢复管理器 — 处理异常恢复逻辑。"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from agent.models import (
    ErrorCategory,
    ErrorInfo,
    ErrorSeverity,
    RecoveryStrategy,
)
from agent.recovery.strategies import execute_recovery, select_strategy

if TYPE_CHECKING:
    from agent.wda.client import WDAClient


class RecoveryManager:
    """恢复管理器 — 管理异常恢复流程。"""

    def __init__(self, wda: WDAClient, max_retries: int = 3, max_recoveries: int = 5):
        self.wda = wda
        self.max_retries = max_retries
        self.max_recoveries = max_recoveries
        self.recovery_count = 0
        self.consecutive_failures = 0

    def handle_error(self, error: ErrorInfo, attempt_count: int = 0) -> RecoveryStrategy:
        """处理错误，返回恢复策略。"""
        # 检查是否超过最大恢复次数
        if self.recovery_count >= self.max_recoveries:
            return RecoveryStrategy.ABORT_TASK
        
        # 检查连续失败次数
        if self.consecutive_failures >= 5:
            return RecoveryStrategy.ABORT_TASK
        
        # 选择恢复策略
        strategy = select_strategy(error, attempt_count)
        
        # 执行恢复
        success = execute_recovery(self.wda, strategy)
        
        if success:
            self.recovery_count += 1
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
        
        return strategy

    def reset(self) -> None:
        """重置恢复计数。"""
        self.recovery_count = 0
        self.consecutive_failures = 0

    def classify_error(self, exception: Exception, context: str = "") -> ErrorInfo:
        """将异常分类为 ErrorInfo。"""
        error_msg = str(exception)
        
        # 根据错误信息分类
        if "element" in error_msg.lower() and "not found" in error_msg.lower():
            category = ErrorCategory.ELEMENT_NOT_FOUND
            severity = ErrorSeverity.LOW
        elif "timeout" in error_msg.lower():
            category = ErrorCategory.TIMEOUT
            severity = ErrorSeverity.MEDIUM
        elif "crash" in error_msg.lower():
            category = ErrorCategory.APP_CRASH
            severity = ErrorSeverity.HIGH
        elif "network" in error_msg.lower() or "connection" in error_msg.lower():
            category = ErrorCategory.NETWORK_ERROR
            severity = ErrorSeverity.MEDIUM
        elif "permission" in error_msg.lower():
            category = ErrorCategory.PERMISSION_DENIED
            severity = ErrorSeverity.HIGH
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.MEDIUM
        
        return ErrorInfo(
            category=category,
            severity=severity,
            code=category.value,
            message=error_msg,
            context=context,
        )
