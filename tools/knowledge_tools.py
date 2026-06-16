"""Knowledge base query tools and task completion."""
from __future__ import annotations


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "task_complete",
        "description": "Signal that the user's task has been completed. Provide a brief summary.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string", "description": "Summary of what was accomplished"},
        }, "required": ["summary"]},
    }},
    {"type": "function", "function": {
        "name": "get_app_info",
        "description": "Get basic information about an app from the knowledge base. Returns app name, bundle_id, description, etc.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle ID (e.g., com.apple.Preferences)"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_page_info",
        "description": "Get information about a specific page/screen in an app. Returns page description, keywords, and key elements.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle ID"},
            "page_name": {"type": "string", "description": "Page name (e.g., '首页', 'WiFi 设置')"},
        }, "required": ["bundle_id", "page_name"]},
    }},
    {"type": "function", "function": {
        "name": "get_operation_flow",
        "description": "Get the operation flow (step-by-step instructions) for a specific task in an app.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle ID"},
            "flow_name": {"type": "string", "description": "Flow name (e.g., '关闭WiFi', '查看设备信息')"},
        }, "required": ["bundle_id", "flow_name"]},
    }},
    {"type": "function", "function": {
        "name": "list_available_apps",
        "description": "List all apps available in the knowledge base.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "list_app_pages",
        "description": "List all known pages/screens for an app.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle ID"},
        }, "required": ["bundle_id"]},
    }},
    {"type": "function", "function": {
        "name": "list_app_flows",
        "description": "List all operation flows available for an app.",
        "parameters": {"type": "object", "properties": {
            "bundle_id": {"type": "string", "description": "App bundle ID"},
        }, "required": ["bundle_id"]},
    }},
]


def create_handlers(executor):
    knowledge = executor.knowledge

    def task_complete(args):
        return f"TASK_COMPLETE: {args.get('summary', '')}"

    def get_app_info(args):
        if not knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        app_info = knowledge.get_app_info(bundle_id)
        if app_info:
            return app_info
        return f"No information found for app: {bundle_id}"

    def get_page_info(args):
        if not knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        page_name = args["page_name"]
        page_info = knowledge.get_page_info(bundle_id, page_name)
        if page_info:
            return page_info
        return f"No information found for page '{page_name}' in app {bundle_id}"

    def get_operation_flow(args):
        if not knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        flow_name = args["flow_name"]
        flow = knowledge.get_operation_flow(bundle_id, flow_name)
        if flow:
            return flow
        return f"No operation flow found for '{flow_name}' in app {bundle_id}"

    def list_available_apps(args):
        if not knowledge:
            return "Knowledge base not available"
        apps = knowledge.get_all_apps()
        if apps:
            return apps
        return "No apps found in knowledge base"

    def list_app_pages(args):
        if not knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        pages = knowledge.get_app_pages(bundle_id)
        if pages:
            return pages
        return f"No pages found for app: {bundle_id}"

    def list_app_flows(args):
        if not knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        flows = knowledge.get_app_flows(bundle_id)
        if flows:
            return flows
        return f"No flows found for app: {bundle_id}"

    return {
        "task_complete": task_complete,
        "get_app_info": get_app_info,
        "get_page_info": get_page_info,
        "get_operation_flow": get_operation_flow,
        "list_available_apps": list_available_apps,
        "list_app_pages": list_app_pages,
        "list_app_flows": list_app_flows,
    }
