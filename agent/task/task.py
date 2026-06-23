"""任务模型定义。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.models import Plan, StepResult, TaskStatus


@dataclass
class Task:
    goal: str
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.CREATED
    params: Dict[str, Any] = field(default_factory=dict)
    plan: Optional[Plan] = None
    results: List[StepResult] = field(default_factory=list)
    priority: int = 5
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def start(self) -> None:
        """启动任务。"""
        if self.status == TaskStatus.CREATED:
            self.status = TaskStatus.RUNNING
            self.started_at = time.time()

    def pause(self) -> None:
        """暂停任务。"""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.PAUSED

    def resume(self) -> None:
        """恢复任务。"""
        if self.status == TaskStatus.PAUSED:
            self.status = TaskStatus.RUNNING

    def complete(self) -> None:
        """标记任务完成。"""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.COMPLETED
            self.completed_at = time.time()

    def fail(self, reason: str = "") -> None:
        """标记任务失败。"""
        if self.status in (TaskStatus.RUNNING, TaskStatus.PAUSED):
            self.status = TaskStatus.FAILED
            self.completed_at = time.time()

    def abort(self) -> None:
        """中止任务。"""
        if self.status in (TaskStatus.RUNNING, TaskStatus.PAUSED):
            self.status = TaskStatus.ABORTED
            self.completed_at = time.time()

    def timeout(self) -> None:
        """任务超时。"""
        if self.status == TaskStatus.RUNNING:
            self.status = TaskStatus.TIMED_OUT
            self.completed_at = time.time()

    def is_running(self) -> bool:
        return self.status == TaskStatus.RUNNING

    def is_finished(self) -> bool:
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.PARTIAL,
            TaskStatus.FAILED,
            TaskStatus.ABORTED,
            TaskStatus.TIMED_OUT,
        )
