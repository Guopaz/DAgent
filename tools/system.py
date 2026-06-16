"""System tools: alerts, keyboard, clipboard, Siri, accessibility, settings, etc."""
from __future__ import annotations


TOOL_SCHEMAS = [
    # ===== Alert =====
    {"type": "function", "function": {
        "name": "get_alert_text",
        "description": "Get the text of the currently displayed alert/dialog.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_alert_text",
        "description": "Set text in an alert's text field.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Text to set"},
        }, "required": ["text"]},
    }},
    {"type": "function", "function": {
        "name": "accept_alert",
        "description": "Accept (OK/Yes) the current alert.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "dismiss_alert",
        "description": "Dismiss (Cancel/No) the current alert.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_alert_buttons",
        "description": "Get the list of buttons in the current alert.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "alert_action",
        "description": "Perform an action on the current alert by button label.",
        "parameters": {"type": "object", "properties": {
            "button_label": {"type": "string", "description": "Button label to press"},
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "clear_alert",
        "description": "Clear the current alert.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},

    # ===== Keyboard =====
    {"type": "function", "function": {
        "name": "dismiss_keyboard",
        "description": "Dismiss the on-screen keyboard.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},

    # ===== Clipboard =====
    {"type": "function", "function": {
        "name": "get_clipboard",
        "description": "Get the current clipboard content.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_clipboard",
        "description": "Set the clipboard content.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Text to set"},
        }, "required": ["text"]},
    }},

    # ===== Siri =====
    {"type": "function", "function": {
        "name": "activate_siri",
        "description": "Activate Siri with a voice command.",
        "parameters": {"type": "object", "properties": {
            "text": {"type": "string", "description": "Voice command text"},
        }, "required": ["text"]},
    }},

    # ===== Accessibility =====
    {"type": "function", "function": {
        "name": "perform_accessibility_audit",
        "description": "Perform an accessibility audit on the current screen.",
        "parameters": {"type": "object", "properties": {
            "audit_types": {"type": "array", "description": "Audit types (optional)"},
        }, "required": []},
    }},

    # ===== Touch ID =====
    {"type": "function", "function": {
        "name": "set_touch_id",
        "description": "Simulate Touch ID authentication (match or non-match).",
        "parameters": {"type": "object", "properties": {
            "match": {"type": "boolean", "description": "Whether to simulate a match (default true)"},
        }, "required": []},
    }},

    # ===== App Switcher =====
    {"type": "function", "function": {
        "name": "activate_app_switcher",
        "description": "Open the app switcher (task manager).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},

    # ===== Logs =====
    {"type": "function", "function": {
        "name": "get_logs",
        "description": "Get device logs (type: syslog, crashlog, etc.).",
        "parameters": {"type": "object", "properties": {
            "log_type": {"type": "string", "description": "Log type (default: syslog)"},
        }, "required": []},
    }},

    # ===== Settings =====
    {"type": "function", "function": {
        "name": "get_settings",
        "description": "Get current session settings.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "update_settings",
        "description": "Update session settings (e.g. snapshot timeout).",
        "parameters": {"type": "object", "properties": {
            "settings": {"type": "object", "description": "Settings key-value pairs"},
        }, "required": ["settings"]},
    }},

    # ===== Timeouts =====
    {"type": "function", "function": {
        "name": "set_timeouts",
        "description": "Set implicit/pageLoad/script timeouts (milliseconds).",
        "parameters": {"type": "object", "properties": {
            "implicit": {"type": "integer", "description": "Implicit wait timeout in ms"},
            "page_load": {"type": "integer", "description": "Page load timeout in ms"},
            "script": {"type": "integer", "description": "Script timeout in ms"},
        }, "required": []},
    }},

    # ===== Utility =====
    {"type": "function", "function": {
        "name": "wait",
        "description": "Pause execution for a given number of seconds. Use this to wait for animations or network responses.",
        "parameters": {"type": "object", "properties": {
            "seconds": {"type": "number", "description": "Seconds to wait (max 10)"},
        }, "required": ["seconds"]},
    }},
]


def create_handlers(executor):
    wda = executor.wda

    def get_alert_text(args):
        return wda.get_alert_text()

    def set_alert_text(args):
        wda.set_alert_text(args["text"])
        return "text set"

    def accept_alert(args):
        wda.accept_alert()
        return "accepted"

    def dismiss_alert(args):
        wda.dismiss_alert()
        return "dismissed"

    def get_alert_buttons(args):
        return wda.get_alert_buttons()

    def alert_action(args):
        wda.alert_action(args.get("button_label"))
        return "action performed"

    def clear_alert(args):
        wda.clear_alert()
        return "cleared"

    def dismiss_keyboard(args):
        wda.dismiss_keyboard()
        return "dismissed"

    def get_clipboard(args):
        return wda.get_clipboard()

    def set_clipboard(args):
        wda.set_clipboard(args["text"])
        return "set"

    def activate_siri(args):
        wda.activate_siri(args["text"])
        return "siri activated"

    def perform_accessibility_audit(args):
        return wda.perform_accessibility_audit(args.get("audit_types"))

    def set_touch_id(args):
        wda.set_touch_id(args.get("match", True))
        return "touch id simulated"

    def activate_app_switcher(args):
        wda.activate_app_switcher()
        return "app switcher opened"

    def get_logs(args):
        return wda.get_logs(args.get("log_type", "syslog"))

    def get_settings(args):
        return wda.get_settings()

    def update_settings(args):
        wda.update_settings(args["settings"])
        return "updated"

    def set_timeouts(args):
        wda.set_timeouts(args.get("implicit"), args.get("page_load"), args.get("script"))
        return "timeouts set"

    def wait(args):
        seconds = min(float(args["seconds"]), 10.0)
        wda.wait(seconds)
        return f"waited {seconds}s"

    return {
        "get_alert_text": get_alert_text,
        "set_alert_text": set_alert_text,
        "accept_alert": accept_alert,
        "dismiss_alert": dismiss_alert,
        "get_alert_buttons": get_alert_buttons,
        "alert_action": alert_action,
        "clear_alert": clear_alert,
        "dismiss_keyboard": dismiss_keyboard,
        "get_clipboard": get_clipboard,
        "set_clipboard": set_clipboard,
        "activate_siri": activate_siri,
        "perform_accessibility_audit": perform_accessibility_audit,
        "set_touch_id": set_touch_id,
        "activate_app_switcher": activate_app_switcher,
        "get_logs": get_logs,
        "get_settings": get_settings,
        "update_settings": update_settings,
        "set_timeouts": set_timeouts,
        "wait": wait,
    }
