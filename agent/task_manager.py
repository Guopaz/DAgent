"""自动从旧 agent.py 拆分生成；按职责维护。"""

from __future__ import annotations

import base64
import json
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from agent.models import *
from agent.loop import AgentLoop

class TaskManager:
    def __init__(self, agent_loop: AgentLoop):
        self.agent_loop = agent_loop
        self.tasks: dict[str, Task] = {}

    def create_task(self, goal: str, params: Optional[Dict[str, Any]] = None, priority: TaskPriority = TaskPriority.NORMAL) -> Task:
        task = Task(goal=goal, params=params or {}, priority=priority)
        self.tasks[task.id] = task
        return task

    def run(self, task: Task) -> bool:
        return self.agent_loop.run_task(task)


