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
from agent.workflow.workflow import Workflow
from agent.helpers import infer_success_criteria

class WorkflowEngine:
    def create_workflow(self, task: Task) -> Workflow:
        max_actions = int(task.params.get("max_actions", 30)) if task.params else 30
        timeout = float(task.params.get("timeout", 600.0)) if task.params else 600.0
        criteria = list(task.params.get("success_criteria", [])) if task.params else []
        constraints = list(task.params.get("constraints", [])) if task.params else []
        if not criteria:
            criteria = infer_success_criteria(task.goal)
        goal = TaskGoal(description=task.goal, success_criteria=criteria, constraints=constraints, max_actions=max_actions, timeout=timeout)
        task.progress.pending_hints = criteria.copy()
        return Workflow(task_id=task.id, goal=goal, progress=task.progress)


