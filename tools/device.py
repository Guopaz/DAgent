"""Device control tools: buttons, screen lock, device info, orientation, location."""
from __future__ import annotations


TOOL_SCHEMAS = [
    # ===== Device Control =====
    {"type": "function", "function": {
        "name": "press_home",
        "description": "Press the home button.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "press_button",
        "description": "Press a hardware button (home, volumeUp, volumeDown, power).",
        "parameters": {"type": "object", "properties": {
            "button_name": {"type": "string", "description": "Button name"},
        }, "required": ["button_name"]},
    }},
    {"type": "function", "function": {
        "name": "deactivate_app",
        "description": "Deactivate the current app (send to background) for a duration.",
        "parameters": {"type": "object", "properties": {
            "duration": {"type": "number", "description": "Duration in seconds (default 3.0)"},
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "lock_screen",
        "description": "Lock the device screen.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "unlock_screen",
        "description": "Unlock the device screen.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "is_locked",
        "description": "Check whether the device screen is locked.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},

    # ===== Screen / Device Info =====
    {"type": "function", "function": {
        "name": "get_screen_info",
        "description": "Get screen information (scale, size).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_active_app_info",
        "description": "Get information about the currently active app.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_battery_info",
        "description": "Get battery information (level, state).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "get_device_info",
        "description": "Get device information (model, name, system version, etc.).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_device_appearance",
        "description": "Set the device appearance (light or dark).",
        "parameters": {"type": "object", "properties": {
            "appearance": {"type": "string", "description": "Appearance: light or dark"},
        }, "required": ["appearance"]},
    }},
    {"type": "function", "function": {
        "name": "get_window_size",
        "description": "Get the current window size (width, height).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},

    # ===== Orientation =====
    {"type": "function", "function": {
        "name": "get_orientation",
        "description": "Get the current device orientation.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_orientation",
        "description": "Set the device orientation.",
        "parameters": {"type": "object", "properties": {
            "orientation": {"type": "string", "description": "Orientation value"},
        }, "required": ["orientation"]},
    }},
    {"type": "function", "function": {
        "name": "get_rotation",
        "description": "Get the current device rotation (x, y, z).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_rotation",
        "description": "Set the device rotation (x, y, z).",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X rotation"},
            "y": {"type": "number", "description": "Y rotation"},
            "z": {"type": "number", "description": "Z rotation"},
        }, "required": []},
    }},

    # ===== Location =====
    {"type": "function", "function": {
        "name": "get_device_location",
        "description": "Get the current device location.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "set_simulated_location",
        "description": "Set a simulated GPS location.",
        "parameters": {"type": "object", "properties": {
            "latitude": {"type": "number", "description": "Latitude"},
            "longitude": {"type": "number", "description": "Longitude"},
        }, "required": ["latitude", "longitude"]},
    }},
    {"type": "function", "function": {
        "name": "get_simulated_location",
        "description": "Get the current simulated GPS location.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "clear_simulated_location",
        "description": "Clear the simulated GPS location.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
]


def create_handlers(executor):
    wda = executor.wda

    def press_home(args):
        wda.press_home()
        return "home pressed"

    def press_button(args):
        wda.press_button(args["button_name"])
        return f"pressed {args['button_name']}"

    def deactivate_app(args):
        wda.deactivate_app(args.get("duration", 3.0))
        return "deactivated"

    def lock_screen(args):
        wda.lock_screen()
        return "locked"

    def unlock_screen(args):
        wda.unlock_screen()
        return "unlocked"

    def is_locked(args):
        return wda.is_locked()

    def get_screen_info(args):
        return wda.get_screen_info()

    def get_active_app_info(args):
        return wda.get_active_app_info()

    def get_battery_info(args):
        return wda.get_battery_info()

    def get_device_info(args):
        return wda.get_device_info()

    def set_device_appearance(args):
        wda.set_device_appearance(args["appearance"])
        return f"appearance set to {args['appearance']}"

    def get_window_size(args):
        return wda.get_window_size()

    def get_orientation(args):
        return wda.get_orientation()

    def set_orientation(args):
        wda.set_orientation(args["orientation"])
        return f"set to {args['orientation']}"

    def get_rotation(args):
        return wda.get_rotation()

    def set_rotation(args):
        wda.set_rotation(args.get("x", 0), args.get("y", 0), args.get("z", 0))
        return "rotation set"

    def get_device_location(args):
        return wda.get_device_location()

    def set_simulated_location(args):
        wda.set_simulated_location(args["latitude"], args["longitude"])
        return "location set"

    def get_simulated_location(args):
        return wda.get_simulated_location()

    def clear_simulated_location(args):
        wda.clear_simulated_location()
        return "cleared"

    return {
        "press_home": press_home,
        "press_button": press_button,
        "deactivate_app": deactivate_app,
        "lock_screen": lock_screen,
        "unlock_screen": unlock_screen,
        "is_locked": is_locked,
        "get_screen_info": get_screen_info,
        "get_active_app_info": get_active_app_info,
        "get_battery_info": get_battery_info,
        "get_device_info": get_device_info,
        "set_device_appearance": set_device_appearance,
        "get_window_size": get_window_size,
        "get_orientation": get_orientation,
        "set_orientation": set_orientation,
        "get_rotation": get_rotation,
        "set_rotation": set_rotation,
        "get_device_location": get_device_location,
        "set_simulated_location": set_simulated_location,
        "get_simulated_location": get_simulated_location,
        "clear_simulated_location": clear_simulated_location,
    }
