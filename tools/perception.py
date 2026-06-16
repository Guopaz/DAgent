"""Perception tools: screenshots and UI source trees."""
from __future__ import annotations


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_screenshot",
        "description": "Capture a screenshot of the current screen. Returns base64-encoded PNG.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_element_screenshot",
        "description": "Capture a screenshot of a specific element. Returns base64-encoded PNG.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_source",
        "description": "Get the current page UI element tree as XML. Use this to understand the page structure.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_accessible_source",
        "description": "Get the accessible UI element tree (without session). Alternative to get_source.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]


def create_handlers(executor):
    wda = executor.wda

    def get_screenshot(args):
        data = wda.get_screenshot()
        if not data:
            return "No screenshot returned"
        if len(data) > 30000:
            return f"[Screenshot captured, base64 length={len(data)}, truncated to save context]"
        return data

    def get_element_screenshot(args):
        data = wda.get_element_screenshot(args["element_id"])
        if not data:
            return "No screenshot returned"
        if len(data) > 30000:
            return f"[Element screenshot captured, base64 length={len(data)}, truncated]"
        return data

    def get_source(args):
        data = wda.get_source()
        if not data:
            return "No source available"
        max_len = 30000
        if len(data) > max_len:
            return data[:max_len] + f"\n... [XML truncated, total length={len(data)}]"
        return data

    def get_accessible_source(args):
        data = wda.get_accessible_source()
        if not data:
            return "No accessible source available"
        max_len = 30000
        if len(data) > max_len:
            return data[:max_len] + f"\n... [Accessible source truncated, total length={len(data)}]"
        return data

    return {
        "get_screenshot": get_screenshot,
        "get_element_screenshot": get_element_screenshot,
        "get_source": get_source,
        "get_accessible_source": get_accessible_source,
    }
