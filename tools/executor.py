"""ToolExecutor core with registration-based dispatch."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Tuple


_registry: dict = {"schemas": [], "handler_factories": []}


def register_tool_module(module) -> None:
    """Register a tool module that exports TOOL_SCHEMAS and create_handlers(executor)."""
    _registry["schemas"].extend(module.TOOL_SCHEMAS)
    _registry["handler_factories"].append(module.create_handlers)


def get_tools() -> list:
    """Return all registered tool schemas for OpenAI function-calling."""
    return [schema for schema in _registry["schemas"]]


class ToolExecutor:
    """Dispatch tool calls to registered handler functions."""

    def __init__(self, wda, knowledge=None):
        self.wda = wda
        self.knowledge = knowledge
        self.handlers: Dict[str, Callable] = {}
        for factory in _registry["handler_factories"]:
            self.handlers.update(factory(self))

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call and return JSON result string."""
        handler = self.handlers.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
        try:
            result = handler(arguments)
            if result is None:
                return json.dumps({"result": "ok"}, ensure_ascii=False)
            result = self._make_json_serializable(result)
            return json.dumps({"result": result}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

    @staticmethod
    def _make_json_serializable(obj):
        """Convert bytes and other non-serializable types to JSON-compatible types."""
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except Exception:
                return obj.hex()
        elif isinstance(obj, dict):
            return {k: ToolExecutor._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [ToolExecutor._make_json_serializable(item) for item in obj]
        return obj
