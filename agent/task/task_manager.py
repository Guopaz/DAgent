"""任务管理器 — 管理任务生命周期。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from agent.models import Plan, StepResult, TaskSnapshot, TaskStatus
from agent.task.task import Task


class TaskManager:
    """任务管理器。"""

    def __init__(self, snapshot_dir: str = "snapshots"):
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: Dict[str, Task] = {}

    def create_task(self, goal: str, params: Optional[Dict] = None, priority: int = 5) -> Task:
        """创建新任务。"""
        task = Task(goal=goal, params=params or {}, priority=priority)
        self._tasks[task.task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务。"""
        return self._tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        """列出任务。"""
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    def save_snapshot(self, task: Task) -> None:
        """保存任务快照。"""
        snapshot = TaskSnapshot(
            task_id=task.task_id,
            status=task.status,
            current_step_index=len(task.results),
            plan=task.plan,
            results=task.results,
            contexts={"goal": task.goal, "params": task.params},
        )
        
        # 保存最新快照
        latest_path = self.snapshot_dir / f"task_{task.task_id}_latest.json"
        with open(latest_path, "w", encoding="utf-8") as f:
            json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)

        # 保存步骤快照
        if task.results:
            step_path = self.snapshot_dir / f"task_{task.task_id}_step_{len(task.results)}.json"
            with open(step_path, "w", encoding="utf-8") as f:
                json.dump(self._snapshot_to_dict(snapshot), f, ensure_ascii=False, indent=2)

    def load_snapshot(self, task_id: str) -> Optional[TaskSnapshot]:
        """加载任务快照。"""
        latest_path = self.snapshot_dir / f"task_{task_id}_latest.json"
        if not latest_path.exists():
            return None

        with open(latest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return self._dict_to_snapshot(data)

    def _snapshot_to_dict(self, snapshot: TaskSnapshot) -> dict:
        """将快照转换为可序列化字典。"""
        return {
            "task_id": snapshot.task_id,
            "status": snapshot.status.value,
            "current_step_index": snapshot.current_step_index,
            "plan": {
                "steps": [
                    {
                        "index": s.index,
                        "description": s.description,
                        "status": s.status,
                        "result_message": s.result_message,
                    }
                    for s in snapshot.plan.steps
                ] if snapshot.plan else [],
                "raw_text": snapshot.plan.raw_text if snapshot.plan else "",
            },
            "results": [
                {
                    "step_index": r.step_index,
                    "success": r.success,
                    "message": r.message,
                    "actions_count": r.actions_count,
                }
                for r in snapshot.results
            ],
            "contexts": snapshot.contexts,
            "timestamp": snapshot.timestamp,
        }

    def _dict_to_snapshot(self, data: dict) -> TaskSnapshot:
        """从字典恢复快照。"""
        from agent.models import PlanStep
        
        plan_data = data.get("plan", {})
        plan = Plan(
            steps=[
                PlanStep(
                    index=s["index"],
                    description=s["description"],
                    status=s["status"],
                    result_message=s.get("result_message", ""),
                )
                for s in plan_data.get("steps", [])
            ],
            raw_text=plan_data.get("raw_text", ""),
        )

        results = [
            StepResult(
                step_index=r["step_index"],
                success=r["success"],
                message=r["message"],
                actions_count=r["actions_count"],
            )
            for r in data.get("results", [])
        ]

        return TaskSnapshot(
            task_id=data["task_id"],
            status=TaskStatus(data["status"]),
            current_step_index=data["current_step_index"],
            plan=plan,
            results=results,
            contexts=data.get("contexts", {}),
            timestamp=data.get("timestamp", 0),
        )
