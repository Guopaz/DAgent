"""App lifecycle management tools."""
from __future__ import annotations


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "launch_app",
        "description": "Launch an app by bundle identifier.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "launch_unattached_app",
        "description": "Launch an app without attaching to it. Optionally pass launch arguments and environment variables.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
            "arguments": {"type": "array", "description": "Launch arguments (optional)"},
            "environment": {"type": "object", "description": "Environment variables (optional)"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "kill_app",
        "description": "Kill (terminate) an app.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "activate_app",
        "description": "Activate (bring to foreground) an app.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "terminate_app",
        "description": "Terminate an app (similar to kill_app).",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_app_state",
        "description": "Get the state of an app (running, background, etc.).",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle identifier"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_apps",
        "description": "List all installed apps.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }}
]


_STATES = {0: "not_installed", 1: "not_running", 2: "background", 3: "suspended", 4: "foreground"}


def create_handlers(executor):
    wda = executor.wda

    def launch_app(args):
        wda.launch_app(args["bundle_id"])
        return "launched"

    def launch_unattached_app(args):
        wda.launch_unattached_app(args["bundle_id"], args.get("arguments"), args.get("environment"))
        return "launched"

    def kill_app(args):
        wda.kill_app(args["bundle_id"])
        return "killed"

    def activate_app(args):
        wda.activate_app(args["bundle_id"])
        return "activated"

    def terminate_app(args):
        return wda.terminate_app(args["bundle_id"])

    def get_app_state(args):
        state = wda.get_app_state(args["bundle_id"])
        return {"state": state, "description": _STATES.get(state, "unknown")}

    def list_apps(args):
        return wda.list_apps()

    return {
        "launch_app": launch_app,
        "launch_unattached_app": launch_unattached_app,
        "kill_app": kill_app,
        "activate_app": activate_app,
        "terminate_app": terminate_app,
        "get_app_state": get_app_state,
        "list_apps": list_apps,
    }
