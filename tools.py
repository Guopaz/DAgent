"""
WDA Tools — OpenAI function-calling schemas + executor for all WDA endpoints.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List

from wda_client import WDAClient


# ── Tool Schemas ────────────────────────────────────────────────────────────

def get_tools() -> list:
    """Return all tool definitions for OpenAI function-calling."""
    return [
        # ===== Perception =====
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

        # ===== Element Finding =====
        {"type": "function", "function": {
            "name": "find_element",
            "description": "Find a single UI element. Strategies: name, xpath, class name, id, predicate string, link text, partial link text. Returns element_id or None.",
            "parameters": {"type": "object", "properties": {
                "using": {"type": "string", "description": "Locator strategy"},
                "value": {"type": "string", "description": "Locator value"},
            }, "required": ["using", "value"]},
        }},
        {"type": "function", "function": {
            "name": "find_elements",
            "description": "Find multiple UI elements matching the criteria.",
            "parameters": {"type": "object", "properties": {
                "using": {"type": "string", "description": "Locator strategy"},
                "value": {"type": "string", "description": "Locator value"},
            }, "required": ["using", "value"]},
        }},
        {"type": "function", "function": {
            "name": "find_element_from_element",
            "description": "Find a child element starting from a parent element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Parent element ID"},
                "using": {"type": "string", "description": "Locator strategy"},
                "value": {"type": "string", "description": "Locator value"},
            }, "required": ["element_id", "using", "value"]},
        }},
        {"type": "function", "function": {
            "name": "find_elements_from_element",
            "description": "Find multiple child elements starting from a parent element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Parent element ID"},
                "using": {"type": "string", "description": "Locator strategy"},
                "value": {"type": "string", "description": "Locator value"},
            }, "required": ["element_id", "using", "value"]},
        }},
        {"type": "function", "function": {
            "name": "get_active_element",
            "description": "Get the currently focused/active element.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "get_visible_cells",
            "description": "Get visible cells within a scrollable element (e.g., table view).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Container element ID"},
            }, "required": ["element_id"]},
        }},

        # ===== Element Properties =====
        {"type": "function", "function": {
            "name": "get_element_text",
            "description": "Get the text content of an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "get_element_attribute",
            "description": "Get an attribute of an element (e.g. label, value, type, enabled, visible, name, identifier).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
                "name": {"type": "string", "description": "Attribute name"},
            }, "required": ["element_id", "name"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_displayed",
            "description": "Check if an element is visible on screen.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_enabled",
            "description": "Check if an element is enabled (interactive).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_selected",
            "description": "Check if an element is selected/checked.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "get_element_name",
            "description": "Get the element type name (e.g. XCUIElementTypeButton).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "get_element_rect",
            "description": "Get element position and size {x, y, width, height}.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_accessible",
            "description": "Check if an element is accessible.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_accessibility_container",
            "description": "Check if an element is an accessibility container.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "is_element_focused",
            "description": "Check if an element currently has focus.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},

        # ===== Element Interaction =====
        {"type": "function", "function": {
            "name": "click_element",
            "description": "Click/tap an element (WebDriver standard click).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "click_element_relative",
            "description": "Click at a relative position within an element (x=0.0-1.0, y=0.0-1.0).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
                "x": {"type": "number", "description": "Relative X (0.0-1.0)"},
                "y": {"type": "number", "description": "Relative Y (0.0-1.0)"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "tap_element",
            "description": "Tap an element (WDA native tap, may work better than click for some controls).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "send_keys",
            "description": "Send text to an element (e.g. a text field).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
                "text": {"type": "string", "description": "Text to type"},
            }, "required": ["element_id", "text"]},
        }},
        {"type": "function", "function": {
            "name": "keyboard_input",
            "description": "Send text to an element via keyboard simulation (may work better for some inputs).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
                "text": {"type": "string", "description": "Text to type"},
            }, "required": ["element_id", "text"]},
        }},
        {"type": "function", "function": {
            "name": "clear_element",
            "description": "Clear the text content of an input element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "focus_element",
            "description": "Set focus on an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Element ID"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "select_pickerwheel",
            "description": "Select a value in a picker wheel. order: 'next' or 'previous'.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Picker wheel element ID"},
                "order": {"type": "string", "enum": ["next", "previous"], "description": "Selection direction"},
                "offset": {"type": "integer", "description": "Number of items to skip (default 1)"},
            }, "required": ["element_id", "order"]},
        }},

        # ===== Coordinate Gestures =====
        {"type": "function", "function": {
            "name": "tap",
            "description": "Tap at specific screen coordinates.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
            }, "required": ["x", "y"]},
        }},
        {"type": "function", "function": {
            "name": "swipe",
            "description": "Perform a swipe gesture from one point to another.",
            "parameters": {"type": "object", "properties": {
                "from_x": {"type": "integer", "description": "Start X"},
                "from_y": {"type": "integer", "description": "Start Y"},
                "to_x": {"type": "integer", "description": "End X"},
                "to_y": {"type": "integer", "description": "End Y"},
                "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
            }, "required": ["from_x", "from_y", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "pinch",
            "description": "Perform a pinch gesture with two coordinates.",
            "parameters": {"type": "object", "properties": {
                "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "duration": {"type": "number"},
            }, "required": ["from_x", "from_y", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "rotate",
            "description": "Perform a rotation gesture with two coordinates.",
            "parameters": {"type": "object", "properties": {
                "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "duration": {"type": "number"},
            }, "required": ["from_x", "from_y", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "double_tap",
            "description": "Double-tap at specific screen coordinates.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
            }, "required": ["x", "y"]},
        }},
        {"type": "function", "function": {
            "name": "two_finger_tap",
            "description": "Two-finger tap at specific screen coordinates.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
            }, "required": ["x", "y"]},
        }},
        {"type": "function", "function": {
            "name": "touch_and_hold",
            "description": "Long-press at specific screen coordinates.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "duration": {"type": "number", "description": "Hold duration in seconds (default 1.0)"},
            }, "required": ["x", "y"]},
        }},
        {"type": "function", "function": {
            "name": "scroll",
            "description": "Scroll the screen in a direction (up, down, left, right).",
            "parameters": {"type": "object", "properties": {
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "distance": {"type": "number", "description": "Scroll distance (0.0-1.0, default 0.5)"},
            }, "required": []},
        }},
        {"type": "function", "function": {
            "name": "drag",
            "description": "Drag from one point to another.",
            "parameters": {"type": "object", "properties": {
                "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "duration": {"type": "number"},
            }, "required": ["from_x", "from_y", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "press_and_drag",
            "description": "Press and drag with specified velocity.",
            "parameters": {"type": "object", "properties": {
                "from_x": {"type": "integer"}, "from_y": {"type": "integer"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "velocity": {"type": "number", "description": "Drag velocity (default 800.0)"},
            }, "required": ["from_x", "from_y", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "force_touch",
            "description": "3D Touch at specific screen coordinates.",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "pressure": {"type": "number", "description": "Pressure (0.0-1.0, default 1.0)"},
                "duration": {"type": "number"},
            }, "required": ["x", "y"]},
        }},
        {"type": "function", "function": {
            "name": "tap_with_number_of_taps",
            "description": "Perform multiple taps at coordinates (e.g. triple tap).",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"},
                "number_of_taps": {"type": "integer", "description": "Number of taps (default 1)"},
                "number_of_touches": {"type": "integer", "description": "Number of fingers (default 1)"},
            }, "required": ["x", "y"]},
        }},

        # ===== Element Gestures =====
        {"type": "function", "function": {
            "name": "swipe_element",
            "description": "Swipe on a specific element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"}, "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "velocity": {"type": "number"},
            }, "required": ["element_id", "direction"]},
        }},
        {"type": "function", "function": {
            "name": "pinch_element",
            "description": "Pinch gesture on an element. scale > 1 zooms in, < 1 zooms out.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "scale": {"type": "number"},
                "velocity": {"type": "number"},
            }, "required": ["element_id", "scale"]},
        }},
        {"type": "function", "function": {
            "name": "rotate_element",
            "description": "Rotate gesture on an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "rotation": {"type": "number", "description": "Rotation in radians"},
                "duration": {"type": "number"},
            }, "required": ["element_id", "rotation"]},
        }},
        {"type": "function", "function": {
            "name": "double_tap_element",
            "description": "Double-tap an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "two_finger_tap_element",
            "description": "Two-finger tap on an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "touch_and_hold_element",
            "description": "Long-press an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "duration": {"type": "number", "description": "Hold duration in seconds (default 1.0)"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "scroll_element",
            "description": "Scroll within an element (e.g. a scroll view or table).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                "distance": {"type": "number", "description": "Scroll distance (0.0-1.0, default 0.5)"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "scroll_to_element",
            "description": "Scroll a container until a target element becomes visible.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string", "description": "Container element ID"},
                "target_element_id": {"type": "string", "description": "Target element ID to scroll to"},
            }, "required": ["element_id", "target_element_id"]},
        }},
        {"type": "function", "function": {
            "name": "drag_element",
            "description": "Drag an element to a target position.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "duration": {"type": "number"},
            }, "required": ["element_id", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "press_and_drag_element",
            "description": "Press and drag an element with specified velocity.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "to_x": {"type": "integer"}, "to_y": {"type": "integer"},
                "velocity": {"type": "number"},
            }, "required": ["element_id", "to_x", "to_y"]},
        }},
        {"type": "function", "function": {
            "name": "force_touch_element",
            "description": "3D Touch on an element.",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "pressure": {"type": "number"},
                "duration": {"type": "number"},
            }, "required": ["element_id"]},
        }},
        {"type": "function", "function": {
            "name": "tap_element_with_number_of_taps",
            "description": "Perform multiple taps on an element (e.g. triple tap).",
            "parameters": {"type": "object", "properties": {
                "element_id": {"type": "string"},
                "number_of_taps": {"type": "integer", "description": "Number of taps (default 1)"},
                "number_of_touches": {"type": "integer", "description": "Number of fingers (default 1)"},
            }, "required": ["element_id"]},
        }},

        # ===== Touch Perform (low-level) =====
        {"type": "function", "function": {
            "name": "touch_perform",
            "description": "Execute a gesture using Appium touch action format. For complex custom gestures.",
            "parameters": {"type": "object", "properties": {
                "actions": {"type": "array", "description": "List of touch action objects"},
            }, "required": ["actions"]},
        }},
        {"type": "function", "function": {
            "name": "touch_multi_perform",
            "description": "Execute a multi-touch gesture.",
            "parameters": {"type": "object", "properties": {
                "actions": {"type": "array", "description": "List of multi-touch action objects"},
            }, "required": ["actions"]},
        }},
        {"type": "function", "function": {
            "name": "w3c_actions",
            "description": "Execute W3C Actions API. For complex pointer/keyboard interactions.",
            "parameters": {"type": "object", "properties": {
                "actions": {"type": "array", "description": "W3C action sequence"},
            }, "required": ["actions"]},
        }},

        # ===== App Management =====
        {"type": "function", "function": {
            "name": "launch_app",
            "description": "Launch an iOS app by bundle ID.",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string", "description": "App bundle ID (e.g. com.apple.Preferences)"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "launch_unattached_app",
            "description": "Launch an app not attached to the current session.",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string"},
                "arguments": {"type": "array", "description": "Launch arguments (optional)"},
                "environment": {"type": "object", "description": "Environment variables (optional)"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "kill_app",
            "description": "Kill an app by bundle ID.",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "activate_app",
            "description": "Bring an app to foreground (activate).",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "terminate_app",
            "description": "Terminate (force close) an app.",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "get_app_state",
            "description": "Get app state: 0=not installed, 1=not running, 2=background, 3=suspended, 4=foreground.",
            "parameters": {"type": "object", "properties": {
                "bundle_id": {"type": "string"},
            }, "required": ["bundle_id"]},
        }},
        {"type": "function", "function": {
            "name": "list_apps",
            "description": "List all installed apps on the device.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},

        # ===== Device Control =====
        {"type": "function", "function": {
            "name": "press_home",
            "description": "Press the Home button.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "press_button",
            "description": "Press a hardware button: home, volumeUp, volumeDown.",
            "parameters": {"type": "object", "properties": {
                "button_name": {"type": "string", "enum": ["home", "volumeUp", "volumeDown"]},
            }, "required": ["button_name"]},
        }},
        {"type": "function", "function": {
            "name": "deactivate_app",
            "description": "Send the current app to background for a duration (seconds).",
            "parameters": {"type": "object", "properties": {
                "duration": {"type": "number", "description": "Background duration in seconds (default 3.0)"},
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
            "description": "Check if the device screen is locked.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},

        # ===== Screen / Device Info =====
        {"type": "function", "function": {
            "name": "get_screen_info",
            "description": "Get screen information (resolution, scale).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "get_active_app_info",
            "description": "Get information about the currently active (foreground) app.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "get_battery_info",
            "description": "Get battery level and state.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "get_device_info",
            "description": "Get device information (model, name, iOS version, etc.).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_device_appearance",
            "description": "Set device appearance style (light or dark mode).",
            "parameters": {"type": "object", "properties": {
                "style": {"type": "string", "enum": ["light", "dark"]},
            }, "required": ["style"]},
        }},
        {"type": "function", "function": {
            "name": "get_window_size",
            "description": "Get the current window/screen size.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},

        # ===== Orientation & Rotation =====
        {"type": "function", "function": {
            "name": "get_orientation",
            "description": "Get current screen orientation (PORTRAIT or LANDSCAPE).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_orientation",
            "description": "Set screen orientation (PORTRAIT or LANDSCAPE).",
            "parameters": {"type": "object", "properties": {
                "orientation": {"type": "string", "enum": ["PORTRAIT", "LANDSCAPE"]},
            }, "required": ["orientation"]},
        }},
        {"type": "function", "function": {
            "name": "get_rotation",
            "description": "Get screen rotation values {x, y, z}.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_rotation",
            "description": "Set screen rotation (x, y, z values).",
            "parameters": {"type": "object", "properties": {
                "x": {"type": "integer"}, "y": {"type": "integer"}, "z": {"type": "integer"},
            }, "required": []},
        }},

        # ===== Location =====
        {"type": "function", "function": {
            "name": "get_device_location",
            "description": "Get the device's real GPS location.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_simulated_location",
            "description": "Set a simulated GPS location for the device.",
            "parameters": {"type": "object", "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            }, "required": ["latitude", "longitude"]},
        }},
        {"type": "function", "function": {
            "name": "get_simulated_location",
            "description": "Get the current simulated GPS location.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "clear_simulated_location",
            "description": "Clear the simulated GPS location (return to real location).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},

        # ===== Alert =====
        {"type": "function", "function": {
            "name": "get_alert_text",
            "description": "Get the text of the current alert/dialog.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_alert_text",
            "description": "Set text in an alert input field.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"},
            }, "required": ["text"]},
        }},
        {"type": "function", "function": {
            "name": "accept_alert",
            "description": "Accept (OK/Yes) the current alert/dialog.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "dismiss_alert",
            "description": "Dismiss (Cancel/No) the current alert/dialog.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "get_alert_buttons",
            "description": "Get the labels of all buttons in the current alert.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "alert_action",
            "description": "Perform an action on an alert by button label.",
            "parameters": {"type": "object", "properties": {
                "button_label": {"type": "string", "description": "Button label to tap"},
            }, "required": []},
        }},
        {"type": "function", "function": {
            "name": "clear_alert",
            "description": "Force clear any visible alert.",
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
            "description": "Get the current clipboard content as text.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }},
        {"type": "function", "function": {
            "name": "set_clipboard",
            "description": "Set text to the clipboard.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string"},
            }, "required": ["text"]},
        }},

        # ===== Siri =====
        {"type": "function", "function": {
            "name": "activate_siri",
            "description": "Activate Siri with a voice command text.",
            "parameters": {"type": "object", "properties": {
                "text": {"type": "string", "description": "Siri command text"},
            }, "required": ["text"]},
        }},

        # ===== Accessibility =====
        {"type": "function", "function": {
            "name": "perform_accessibility_audit",
            "description": "Run an accessibility audit on the current screen.",
            "parameters": {"type": "object", "properties": {
                "audit_types": {"type": "array", "description": "Audit types to run (optional)"},
            }, "required": []},
        }},

        # ===== Touch ID =====
        {"type": "function", "function": {
            "name": "set_touch_id",
            "description": "Simulate Touch ID (simulator only). match=true for success, false for failure.",
            "parameters": {"type": "object", "properties": {
                "match": {"type": "boolean", "description": "Whether the fingerprint matches"},
            }, "required": []},
        }},

        # ===== App Switcher =====
        {"type": "function", "function": {
            "name": "activate_app_switcher",
            "description": "Open the app switcher (multitasking view).",
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
        {"type": "function", "function": {
            "name": "task_complete",
            "description": "Signal that the user's task has been completed. Provide a brief summary.",
            "parameters": {"type": "object", "properties": {
                "summary": {"type": "string", "description": "Summary of what was accomplished"},
            }, "required": ["summary"]},
        }},

        # Knowledge Base Query
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


# ── Executor ────────────────────────────────────────────────────────────────

class ToolExecutor:
    """Dispatch tool calls to WDAClient methods."""

    def __init__(self, wda: WDAClient):
        self.wda = wda
        self.handlers: Dict[str, Any] = {
            # Perception
            "get_screenshot":            self._get_screenshot,
            "get_element_screenshot":    self._get_element_screenshot,
            "get_source":                self._get_source,
            "get_accessible_source":     self._get_accessible_source,
            # Element Finding
            "find_element":              self._find_element,
            "find_elements":             self._find_elements,
            "find_element_from_element": self._find_element_from_element,
            "find_elements_from_element":self._find_elements_from_element,
            "get_active_element":        self._get_active_element,
            "get_visible_cells":         self._get_visible_cells,
            # Element Properties
            "get_element_text":          self._get_element_text,
            "get_element_attribute":     self._get_element_attribute,
            "is_element_displayed":      self._is_element_displayed,
            "is_element_enabled":        self._is_element_enabled,
            "is_element_selected":       self._is_element_selected,
            "get_element_name":          self._get_element_name,
            "get_element_rect":          self._get_element_rect,
            "is_element_accessible":     self._is_element_accessible,
            "is_element_accessibility_container": self._is_element_accessibility_container,
            "is_element_focused":        self._is_element_focused,
            # Element Interaction
            "click_element":             self._click_element,
            "click_element_relative":    self._click_element_relative,
            "tap_element":               self._tap_element,
            "send_keys":                 self._send_keys,
            "keyboard_input":            self._keyboard_input,
            "clear_element":             self._clear_element,
            "focus_element":             self._focus_element,
            "select_pickerwheel":        self._select_pickerwheel,
            # Coordinate Gestures
            "tap":                       self._tap,
            "swipe":                     self._swipe,
            "pinch":                     self._pinch,
            "rotate":                    self._rotate,
            "double_tap":                self._double_tap,
            "two_finger_tap":            self._two_finger_tap,
            "touch_and_hold":            self._touch_and_hold,
            "scroll":                    self._scroll,
            "drag":                      self._drag,
            "press_and_drag":            self._press_and_drag,
            "force_touch":               self._force_touch,
            "tap_with_number_of_taps":   self._tap_with_number_of_taps,
            # Element Gestures
            "swipe_element":             self._swipe_element,
            "pinch_element":             self._pinch_element,
            "rotate_element":            self._rotate_element,
            "double_tap_element":        self._double_tap_element,
            "two_finger_tap_element":    self._two_finger_tap_element,
            "touch_and_hold_element":    self._touch_and_hold_element,
            "scroll_element":            self._scroll_element,
            "scroll_to_element":         self._scroll_to_element,
            "drag_element":              self._drag_element,
            "press_and_drag_element":    self._press_and_drag_element,
            "force_touch_element":       self._force_touch_element,
            "tap_element_with_number_of_taps": self._tap_element_with_number_of_taps,
            # Touch Perform
            "touch_perform":             self._touch_perform,
            "touch_multi_perform":       self._touch_multi_perform,
            "w3c_actions":               self._w3c_actions,
            # App Management
            "launch_app":                self._launch_app,
            "launch_unattached_app":     self._launch_unattached_app,
            "kill_app":                  self._kill_app,
            "activate_app":              self._activate_app,
            "terminate_app":             self._terminate_app,
            "get_app_state":             self._get_app_state,
            "list_apps":                 self._list_apps,
            # Device Control
            "press_home":                self._press_home,
            "press_button":              self._press_button,
            "deactivate_app":            self._deactivate_app,
            "lock_screen":               self._lock_screen,
            "unlock_screen":             self._unlock_screen,
            "is_locked":                 self._is_locked,
            # Screen / Device Info
            "get_screen_info":           self._get_screen_info,
            "get_active_app_info":       self._get_active_app_info,
            "get_battery_info":          self._get_battery_info,
            "get_device_info":           self._get_device_info,
            "set_device_appearance":     self._set_device_appearance,
            "get_window_size":           self._get_window_size,
            # Orientation
            "get_orientation":           self._get_orientation,
            "set_orientation":           self._set_orientation,
            "get_rotation":              self._get_rotation,
            "set_rotation":              self._set_rotation,
            # Location
            "get_device_location":       self._get_device_location,
            "set_simulated_location":    self._set_simulated_location,
            "get_simulated_location":    self._get_simulated_location,
            "clear_simulated_location":  self._clear_simulated_location,
            # Alert
            "get_alert_text":            self._get_alert_text,
            "set_alert_text":            self._set_alert_text,
            "accept_alert":              self._accept_alert,
            "dismiss_alert":             self._dismiss_alert,
            "get_alert_buttons":         self._get_alert_buttons,
            "alert_action":              self._alert_action,
            "clear_alert":               self._clear_alert,
            # Keyboard
            "dismiss_keyboard":          self._dismiss_keyboard,
            # Clipboard
            "get_clipboard":             self._get_clipboard,
            "set_clipboard":             self._set_clipboard,
            # Siri
            "activate_siri":             self._activate_siri,
            # Accessibility
            "perform_accessibility_audit": self._perform_accessibility_audit,
            # Touch ID
            "set_touch_id":              self._set_touch_id,
            # App Switcher
            "activate_app_switcher":     self._activate_app_switcher,
            # Logs
            "get_logs":                  self._get_logs,
            # Settings
            "get_settings":              self._get_settings,
            "update_settings":           self._update_settings,
            # Timeouts
            "set_timeouts":              self._set_timeouts,
            # Utility
            "wait":                      self._wait,
            "task_complete":             self._task_complete,
            # Knowledge Base Query
            "get_app_info":            self._get_app_info,
            "get_page_info":           self._get_page_info,
            "get_operation_flow":      self._get_operation_flow,
            "list_available_apps":     self._list_available_apps,
            "list_app_pages":          self._list_app_pages,
            "list_app_flows":          self._list_app_flows,
        }

    def _make_json_serializable(self, obj):
        """Convert bytes and other non-serializable types to JSON-compatible types."""
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8')
            except:
                return obj.hex()
        elif isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return [self._make_json_serializable(item) for item in obj]
        return obj

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool call and return JSON result string."""
        handler = self.handlers.get(tool_name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {tool_name}"}, ensure_ascii=False)
        try:
            result = handler(arguments)
            if result is None:
                return json.dumps({"result": "ok"}, ensure_ascii=False)
            # Convert bytes and other non-serializable types
            result = self._make_json_serializable(result)
            return json.dumps({"result": result}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)

    # ── Handler implementations ──────────────────────────────────────────────

    def _get_screenshot(self, args):
        data = self.wda.get_screenshot()
        if not data:
            return "No screenshot returned"
        if len(data) > 5000:
            return f"[Screenshot captured, base64 length={len(data)}, truncated to save context]"
        return data

    def _get_element_screenshot(self, args):
        data = self.wda.get_element_screenshot(args["element_id"])
        if not data:
            return "No screenshot returned"
        if len(data) > 5000:
            return f"[Element screenshot captured, base64 length={len(data)}, truncated]"
        return data

    def _get_source(self, args):
        data = self.wda.get_source()
        if not data:
            return "No source available"
        # Truncate to avoid overwhelming the context
        max_len = 8000
        if len(data) > max_len:
            return data[:max_len] + f"\n... [XML truncated, total length={len(data)}]"
        return data

    def _get_accessible_source(self, args):
        data = self.wda.get_accessible_source()
        if not data:
            return "No accessible source available"
        max_len = 8000
        if len(data) > max_len:
            return data[:max_len] + f"\n... [Accessible source truncated, total length={len(data)}]"
        return data

    def _find_element(self, args):
        eid = self.wda.find_element(args["using"], args["value"])
        return {"element_id": eid} if eid else None

    def _find_elements(self, args):
        return self.wda.find_elements(args["using"], args["value"])

    def _find_element_from_element(self, args):
        eid = self.wda.find_element_from_element(args["element_id"], args["using"], args["value"])
        return {"element_id": eid} if eid else None

    def _find_elements_from_element(self, args):
        return self.wda.find_elements_from_element(args["element_id"], args["using"], args["value"])

    def _get_active_element(self, args):
        eid = self.wda.get_active_element()
        return {"element_id": eid} if eid else None

    def _get_visible_cells(self, args):
        return self.wda.get_visible_cells(args["element_id"])

    def _get_element_text(self, args):
        return self.wda.get_element_text(args["element_id"])

    def _get_element_attribute(self, args):
        return self.wda.get_element_attribute(args["element_id"], args["name"])

    def _is_element_displayed(self, args):
        return self.wda.is_element_displayed(args["element_id"])

    def _is_element_enabled(self, args):
        return self.wda.is_element_enabled(args["element_id"])

    def _is_element_selected(self, args):
        return self.wda.is_element_selected(args["element_id"])

    def _get_element_name(self, args):
        return self.wda.get_element_name(args["element_id"])

    def _get_element_rect(self, args):
        return self.wda.get_element_rect(args["element_id"])

    def _is_element_accessible(self, args):
        return self.wda.is_element_accessible(args["element_id"])

    def _is_element_accessibility_container(self, args):
        return self.wda.is_element_accessibility_container(args["element_id"])

    def _is_element_focused(self, args):
        return self.wda.is_element_focused(args["element_id"])

    def _click_element(self, args):
        self.wda.click_element(args["element_id"])
        return "clicked"

    def _click_element_relative(self, args):
        self.wda.click_element_relative(args["element_id"], args.get("x", 0.5), args.get("y", 0.5))
        return "clicked"

    def _tap_element(self, args):
        self.wda.tap_element(args["element_id"])
        return "tapped"

    def _send_keys(self, args):
        self.wda.send_keys(args["element_id"], args["text"])
        return "sent"

    def _keyboard_input(self, args):
        self.wda.keyboard_input(args["element_id"], args["text"])
        return "input sent"

    def _clear_element(self, args):
        self.wda.clear_element(args["element_id"])
        return "cleared"

    def _focus_element(self, args):
        self.wda.focus_element(args["element_id"])
        return "focused"

    def _select_pickerwheel(self, args):
        self.wda.select_pickerwheel(args["element_id"], args["order"], args.get("offset", 1))
        return "selected"

    def _tap(self, args):
        self.wda.tap(args["x"], args["y"])
        return "tapped"

    def _swipe(self, args):
        self.wda.swipe(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "swiped"

    def _pinch(self, args):
        self.wda.pinch(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "pinched"

    def _rotate(self, args):
        self.wda.rotate(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "rotated"

    def _double_tap(self, args):
        self.wda.double_tap(args["x"], args["y"])
        return "double tapped"

    def _two_finger_tap(self, args):
        self.wda.two_finger_tap(args["x"], args["y"])
        return "two finger tapped"

    def _touch_and_hold(self, args):
        self.wda.touch_and_hold(args["x"], args["y"], args.get("duration", 1.0))
        return "held"

    def _scroll(self, args):
        self.wda.scroll(args.get("direction", "down"), args.get("distance", 0.5))
        return "scrolled"

    def _drag(self, args):
        self.wda.drag(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "dragged"

    def _press_and_drag(self, args):
        self.wda.press_and_drag(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("velocity", 800.0))
        return "pressed and dragged"

    def _force_touch(self, args):
        self.wda.force_touch(args["x"], args["y"], args.get("pressure", 1.0), args.get("duration", 1.0))
        return "force touched"

    def _tap_with_number_of_taps(self, args):
        self.wda.tap_with_number_of_taps(args["x"], args["y"], args.get("number_of_taps", 1), args.get("number_of_touches", 1))
        return "tapped"

    def _swipe_element(self, args):
        self.wda.swipe_element(args["element_id"], args["direction"], args.get("velocity", 1.0))
        return "swiped"

    def _pinch_element(self, args):
        self.wda.pinch_element(args["element_id"], args["scale"], args.get("velocity", 1.0))
        return "pinched"

    def _rotate_element(self, args):
        self.wda.rotate_element(args["element_id"], args["rotation"], args.get("duration", 1.0))
        return "rotated"

    def _double_tap_element(self, args):
        self.wda.double_tap_element(args["element_id"])
        return "double tapped"

    def _two_finger_tap_element(self, args):
        self.wda.two_finger_tap_element(args["element_id"])
        return "two finger tapped"

    def _touch_and_hold_element(self, args):
        self.wda.touch_and_hold_element(args["element_id"], args.get("duration", 1.0))
        return "held"

    def _scroll_element(self, args):
        self.wda.scroll_element(args["element_id"], args.get("direction", "down"), args.get("distance", 0.5))
        return "scrolled"

    def _scroll_to_element(self, args):
        self.wda.scroll_to_element(args["element_id"], args["target_element_id"])
        return "scrolled to element"

    def _drag_element(self, args):
        self.wda.drag_element(args["element_id"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "dragged"

    def _press_and_drag_element(self, args):
        self.wda.press_and_drag_element(args["element_id"], args["to_x"], args["to_y"], args.get("velocity", 800.0))
        return "pressed and dragged"

    def _force_touch_element(self, args):
        self.wda.force_touch_element(args["element_id"], args.get("pressure", 1.0), args.get("duration", 1.0))
        return "force touched"

    def _tap_element_with_number_of_taps(self, args):
        self.wda.tap_element_with_number_of_taps(args["element_id"], args.get("number_of_taps", 1), args.get("number_of_touches", 1))
        return "tapped"

    def _touch_perform(self, args):
        self.wda.touch_perform(args["actions"])
        return "performed"

    def _touch_multi_perform(self, args):
        self.wda.touch_multi_perform(args["actions"])
        return "performed"

    def _w3c_actions(self, args):
        self.wda.w3c_actions(args["actions"])
        return "performed"

    def _launch_app(self, args):
        self.wda.launch_app(args["bundle_id"])
        return "launched"

    def _launch_unattached_app(self, args):
        self.wda.launch_unattached_app(args["bundle_id"], args.get("arguments"), args.get("environment"))
        return "launched"

    def _kill_app(self, args):
        self.wda.kill_app(args["bundle_id"])
        return "killed"

    def _activate_app(self, args):
        self.wda.activate_app(args["bundle_id"])
        return "activated"

    def _terminate_app(self, args):
        return self.wda.terminate_app(args["bundle_id"])

    def _get_app_state(self, args):
        state = self.wda.get_app_state(args["bundle_id"])
        states = {0: "not_installed", 1: "not_running", 2: "background", 3: "suspended", 4: "foreground"}
        return {"state": state, "description": states.get(state, "unknown")}

    def _list_apps(self, args):
        return self.wda.list_apps()

    def _press_home(self, args):
        self.wda.press_home()
        return "home pressed"

    def _press_button(self, args):
        self.wda.press_button(args["button_name"])
        return f"pressed {args['button_name']}"

    def _deactivate_app(self, args):
        self.wda.deactivate_app(args.get("duration", 3.0))
        return "deactivated"

    def _lock_screen(self, args):
        self.wda.lock_screen()
        return "locked"

    def _unlock_screen(self, args):
        self.wda.unlock_screen()
        return "unlocked"

    def _is_locked(self, args):
        return self.wda.is_locked()

    def _get_screen_info(self, args):
        return self.wda.get_screen_info()

    def _get_active_app_info(self, args):
        return self.wda.get_active_app_info()

    def _get_battery_info(self, args):
        return self.wda.get_battery_info()

    def _get_device_info(self, args):
        return self.wda.get_device_info()

    def _set_device_appearance(self, args):
        self.wda.set_device_appearance(args["style"])
        return f"set to {args['style']}"

    def _get_window_size(self, args):
        return self.wda.get_window_size()

    def _get_orientation(self, args):
        return self.wda.get_orientation()

    def _set_orientation(self, args):
        self.wda.set_orientation(args["orientation"])
        return f"set to {args['orientation']}"

    def _get_rotation(self, args):
        return self.wda.get_rotation()

    def _set_rotation(self, args):
        self.wda.set_rotation(args.get("x", 0), args.get("y", 0), args.get("z", 0))
        return "rotation set"

    def _get_device_location(self, args):
        return self.wda.get_device_location()

    def _set_simulated_location(self, args):
        self.wda.set_simulated_location(args["latitude"], args["longitude"])
        return "location set"

    def _get_simulated_location(self, args):
        return self.wda.get_simulated_location()

    def _clear_simulated_location(self, args):
        self.wda.clear_simulated_location()
        return "cleared"

    def _get_alert_text(self, args):
        return self.wda.get_alert_text()

    def _set_alert_text(self, args):
        self.wda.set_alert_text(args["text"])
        return "text set"

    def _accept_alert(self, args):
        self.wda.accept_alert()
        return "accepted"

    def _dismiss_alert(self, args):
        self.wda.dismiss_alert()
        return "dismissed"

    def _get_alert_buttons(self, args):
        return self.wda.get_alert_buttons()

    def _alert_action(self, args):
        self.wda.alert_action(args.get("button_label"))
        return "action performed"

    def _clear_alert(self, args):
        self.wda.clear_alert()
        return "cleared"

    def _dismiss_keyboard(self, args):
        self.wda.dismiss_keyboard()
        return "dismissed"

    def _get_clipboard(self, args):
        return self.wda.get_clipboard()

    def _set_clipboard(self, args):
        self.wda.set_clipboard(args["text"])
        return "set"

    def _activate_siri(self, args):
        self.wda.activate_siri(args["text"])
        return "siri activated"

    def _perform_accessibility_audit(self, args):
        return self.wda.perform_accessibility_audit(args.get("audit_types"))

    def _set_touch_id(self, args):
        self.wda.set_touch_id(args.get("match", True))
        return "touch id simulated"

    def _activate_app_switcher(self, args):
        self.wda.activate_app_switcher()
        return "app switcher opened"

    def _get_logs(self, args):
        return self.wda.get_logs(args.get("log_type", "syslog"))

    def _get_settings(self, args):
        return self.wda.get_settings()

    def _update_settings(self, args):
        self.wda.update_settings(args["settings"])
        return "updated"

    def _set_timeouts(self, args):
        self.wda.set_timeouts(args.get("implicit"), args.get("page_load"), args.get("script"))
        return "timeouts set"

    def _wait(self, args):
        seconds = min(float(args["seconds"]), 10.0)
        self.wda.wait(seconds)
        return f"waited {seconds}s"


    # Knowledge Base Handlers
    def _get_app_info(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        app_info = self.knowledge.get_app_info(bundle_id)
        if app_info:
            return app_info
        return f"No information found for app: {bundle_id}"

    def _get_page_info(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        page_name = args["page_name"]
        page_info = self.knowledge.get_page_info(bundle_id, page_name)
        if page_info:
            return page_info
        return f"No information found for page '{page_name}' in app {bundle_id}"

    def _get_operation_flow(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        flow_name = args["flow_name"]
        flow = self.knowledge.get_operation_flow(bundle_id, flow_name)
        if flow:
            return flow
        return f"No operation flow found for '{flow_name}' in app {bundle_id}"

    def _list_available_apps(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        apps = self.knowledge.get_all_apps()
        if apps:
            return apps
        return "No apps found in knowledge base"

    def _list_app_pages(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        pages = self.knowledge.get_app_pages(bundle_id)
        if pages:
            return pages
        return f"No pages found for app: {bundle_id}"

    def _list_app_flows(self, args):
        if not self.knowledge:
            return "Knowledge base not available"
        bundle_id = args["bundle_id"]
        flows = self.knowledge.get_app_flows(bundle_id)
        if flows:
            return flows
        return f"No flows found for app: {bundle_id}"

    def _task_complete(self, args):
        return f"TASK_COMPLETE: {args.get('summary', '')}"
