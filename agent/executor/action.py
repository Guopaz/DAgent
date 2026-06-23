"""动作模型 — 定义所有可执行的动作类型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from agent.models import ActionType


@dataclass
class ActionSpec:
    """动作规格 — 描述一个具体动作。"""
    action_type: ActionType
    target: str = ""
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
