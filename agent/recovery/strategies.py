"""恢复策略 — 定义各种异常恢复策略。"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Optional

from agent.models import ErrorInfo, ErrorSeverity, RecoveryStrategy

if TYPE_CHECKING:
    from agent.wda.client import WDAClient


class RecoveryAction:
    """恢复动作 — 描述一个具体的恢复操作。"""

    def __init__(self, strategy: RecoveryStrategy, description: str):
        self.strategy = strategy
        self.description = description


def select_strategy(error: ErrorInfo, attempt_count: int = 0) -> RecoveryStrategy:
    """根据错误类型和严重程度选择恢复策略。"""
    severity = error.severity
    category = error.category
    
    # LOW 严重度：自动重试
    if severity == ErrorSeverity.LOW:
        if attempt_count < 3:
            return RecoveryStrategy.RETRY
        return RecoveryStrategy.SKIP_STEP
    
    # MEDIUM 严重度：尝试重试或跳过
    if severity == ErrorSeverity.MEDIUM:
        if attempt_count < 2:
            return RecoveryStrategy.RETRY
        return RecoveryStrategy.SKIP_STEP
    
    # HIGH 严重度：重新规划或跳过
    if severity == ErrorSeverity.HIGH:
        if attempt_count < 1:
            return RecoveryStrategy.REPLAN
        return RecoveryStrategy.SKIP_STEP
    
    # CRITICAL 严重度：终止任务
    if severity == ErrorSeverity.CRITICAL:
        return RecoveryStrategy.ABORT_TASK
    
    return RecoveryStrategy.RETRY


def execute_recovery(wda: WDAClient, strategy: RecoveryStrategy) -> bool:
    """执行恢复策略。"""
    try:
        if strategy == RecoveryStrategy.RETRY:
            time.sleep(1)
            return True
        
        if strategy == RecoveryStrategy.SKIP_STEP:
            return True
        
        if strategy == RecoveryStrategy.GO_HOME:
            wda.go_home()
            time.sleep(2)
            return True
        
        if strategy == RecoveryStrategy.RESTART_APP:
            # 获取当前应用并重启
            try:
                app_info = wda.get_active_app_info()
                bundle_id = app_info.get("bundle_id", "")
                if bundle_id:
                    wda.terminate_app(bundle_id)
                    time.sleep(1)
                    wda.launch_app(bundle_id)
                    time.sleep(3)
                    return True
            except Exception:
                pass
            return False
        
        if strategy == RecoveryStrategy.REPLAN:
            return True
        
        if strategy == RecoveryStrategy.ABORT_TASK:
            return True
        
        return False
    except Exception:
        return False
