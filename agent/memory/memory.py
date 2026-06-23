"""记忆系统 — 上下文管理与历史追踪。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional

from agent.models import ActionRecord, Observation


@dataclass
class MemoryEntry:
    """记忆条目。"""
    observation: Optional[Observation] = None
    action: Optional[ActionRecord] = None
    timestamp: float = 0.0
    context: str = ""


class Memory:
    """上下文记忆系统。"""

    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.history: Deque[MemoryEntry] = deque(maxlen=max_history)
        self.current_observation: Optional[Observation] = None
        self.metadata: Dict[str, any] = {}

    def record_observation(self, observation: Observation) -> None:
        """记录观察。"""
        entry = MemoryEntry(
            observation=observation,
            timestamp=observation.timestamp,
            context="observation",
        )
        self.history.append(entry)
        self.current_observation = observation

    def record_action(self, action: ActionRecord) -> None:
        """记录动作。"""
        entry = MemoryEntry(
            action=action,
            timestamp=action.timestamp,
            context="action",
        )
        self.history.append(entry)

    def get_recent_actions(self, count: int = 5) -> List[ActionRecord]:
        """获取最近的动作记录。"""
        actions = []
        for entry in reversed(self.history):
            if entry.action:
                actions.append(entry.action)
                if len(actions) >= count:
                    break
        return list(reversed(actions))

    def get_recent_observations(self, count: int = 5) -> List[Observation]:
        """获取最近的观察记录。"""
        observations = []
        for entry in reversed(self.history):
            if entry.observation:
                observations.append(entry.observation)
                if len(observations) >= count:
                    break
        return list(reversed(observations))

    def get_action_history_text(self, count: int = 5) -> str:
        """生成动作历史文本。"""
        actions = self.get_recent_actions(count)
        if not actions:
            return "无历史动作"

        lines = []
        for i, action in enumerate(actions, 1):
            result_text = "成功" if action.result and action.result.success else "失败"
            lines.append(
                f"{i}. {action.tool_name}: {action.parameters} → {result_text}"
            )
        return "\n".join(lines)

    def clear(self) -> None:
        """清空记忆。"""
        self.history.clear()
        self.current_observation = None
        self.metadata.clear()

    def set_metadata(self, key: str, value: any) -> None:
        """设置元数据。"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: any = None) -> any:
        """获取元数据。"""
        return self.metadata.get(key, default)
