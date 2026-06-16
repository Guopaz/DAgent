"""Gesture tools: coordinate-based and element-based touch interactions."""
from __future__ import annotations


TOOL_SCHEMAS = [
    # ===== Coordinate Gestures =====
    {"type": "function", "function": {
        "name": "tap",
        "description": "Tap at specific screen coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
        }, "required": ["x", "y"]},
    }},
    {"type": "function", "function": {
        "name": "swipe",
        "description": "Swipe from one coordinate to another.",
        "parameters": {"type": "object", "properties": {
            "from_x": {"type": "number", "description": "Starting X coordinate"},
            "from_y": {"type": "number", "description": "Starting Y coordinate"},
            "to_x": {"type": "number", "description": "Ending X coordinate"},
            "to_y": {"type": "number", "description": "Ending Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["from_x", "from_y", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "pinch",
        "description": "Pinch gesture from one coordinate to another.",
        "parameters": {"type": "object", "properties": {
            "from_x": {"type": "number", "description": "Starting X coordinate"},
            "from_y": {"type": "number", "description": "Starting Y coordinate"},
            "to_x": {"type": "number", "description": "Ending X coordinate"},
            "to_y": {"type": "number", "description": "Ending Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["from_x", "from_y", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "rotate",
        "description": "Rotate gesture from one coordinate to another.",
        "parameters": {"type": "object", "properties": {
            "from_x": {"type": "number", "description": "Starting X coordinate"},
            "from_y": {"type": "number", "description": "Starting Y coordinate"},
            "to_x": {"type": "number", "description": "Ending X coordinate"},
            "to_y": {"type": "number", "description": "Ending Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["from_x", "from_y", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "double_tap",
        "description": "Double tap at specific screen coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
        }, "required": ["x", "y"]},
    }},
    {"type": "function", "function": {
        "name": "two_finger_tap",
        "description": "Two-finger tap at specific screen coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
        }, "required": ["x", "y"]},
    }},
    {"type": "function", "function": {
        "name": "touch_and_hold",
        "description": "Touch and hold at specific screen coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["x", "y"]},
    }},
    {"type": "function", "function": {
        "name": "scroll",
        "description": "Scroll in a direction (up, down, left, right).",
        "parameters": {"type": "object", "properties": {
            "direction": {"type": "string", "description": "Direction: up, down, left, right (default down)"},
            "distance": {"type": "number", "description": "Distance as fraction of screen (default 0.5)"},
        }, "required": []},
    }},
    {"type": "function", "function": {
        "name": "drag",
        "description": "Drag from one coordinate to another.",
        "parameters": {"type": "object", "properties": {
            "from_x": {"type": "number", "description": "Starting X coordinate"},
            "from_y": {"type": "number", "description": "Starting Y coordinate"},
            "to_x": {"type": "number", "description": "Ending X coordinate"},
            "to_y": {"type": "number", "description": "Ending Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["from_x", "from_y", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "press_and_drag",
        "description": "Press and drag from one coordinate to another with velocity.",
        "parameters": {"type": "object", "properties": {
            "from_x": {"type": "number", "description": "Starting X coordinate"},
            "from_y": {"type": "number", "description": "Starting Y coordinate"},
            "to_x": {"type": "number", "description": "Ending X coordinate"},
            "to_y": {"type": "number", "description": "Ending Y coordinate"},
            "velocity": {"type": "number", "description": "Velocity in pixels per second (default 800.0)"},
        }, "required": ["from_x", "from_y", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "force_touch",
        "description": "Force touch (3D touch) at specific coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
            "pressure": {"type": "number", "description": "Pressure (default 1.0)"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["x", "y"]},
    }},
    {"type": "function", "function": {
        "name": "tap_with_number_of_taps",
        "description": "Tap multiple times at specific coordinates.",
        "parameters": {"type": "object", "properties": {
            "x": {"type": "number", "description": "X coordinate"},
            "y": {"type": "number", "description": "Y coordinate"},
            "number_of_taps": {"type": "integer", "description": "Number of taps (default 1)"},
            "number_of_touches": {"type": "integer", "description": "Number of fingers (default 1)"},
        }, "required": ["x", "y"]},
    }},

    # ===== Element Gestures =====
    {"type": "function", "function": {
        "name": "swipe_element",
        "description": "Swipe an element in a direction.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "direction": {"type": "string", "description": "Direction: up, down, left, right"},
            "velocity": {"type": "number", "description": "Velocity (default 1.0)"},
        }, "required": ["element_id", "direction"]},
    }},
    {"type": "function", "function": {
        "name": "pinch_element",
        "description": "Pinch an element with a scale factor.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "scale": {"type": "number", "description": "Scale factor"},
            "velocity": {"type": "number", "description": "Velocity (default 1.0)"},
        }, "required": ["element_id", "scale"]},
    }},
    {"type": "function", "function": {
        "name": "rotate_element",
        "description": "Rotate an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "rotation": {"type": "number", "description": "Rotation angle"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["element_id", "rotation"]},
    }},
    {"type": "function", "function": {
        "name": "double_tap_element",
        "description": "Double tap on an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "two_finger_tap_element",
        "description": "Two-finger tap on an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "touch_and_hold_element",
        "description": "Touch and hold on an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "scroll_element",
        "description": "Scroll an element in a direction.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "direction": {"type": "string", "description": "Direction: up, down, left, right (default down)"},
            "distance": {"type": "number", "description": "Distance as fraction (default 0.5)"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "scroll_to_element",
        "description": "Scroll to make a target element visible.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Source element ID (container)"},
            "target_element_id": {"type": "string", "description": "Target element ID to scroll to"},
        }, "required": ["element_id", "target_element_id"]},
    }},
    {"type": "function", "function": {
        "name": "drag_element",
        "description": "Drag an element to specific coordinates.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "to_x": {"type": "number", "description": "Target X coordinate"},
            "to_y": {"type": "number", "description": "Target Y coordinate"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["element_id", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "press_and_drag_element",
        "description": "Press and drag an element to specific coordinates.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "to_x": {"type": "number", "description": "Target X coordinate"},
            "to_y": {"type": "number", "description": "Target Y coordinate"},
            "velocity": {"type": "number", "description": "Velocity in pixels per second (default 800.0)"},
        }, "required": ["element_id", "to_x", "to_y"]},
    }},
    {"type": "function", "function": {
        "name": "force_touch_element",
        "description": "Force touch (3D touch) on an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "pressure": {"type": "number", "description": "Pressure (default 1.0)"},
            "duration": {"type": "number", "description": "Duration in seconds (default 1.0)"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "tap_element_with_number_of_taps",
        "description": "Tap an element multiple times.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "number_of_taps": {"type": "integer", "description": "Number of taps (default 1)"},
            "number_of_touches": {"type": "integer", "description": "Number of fingers (default 1)"},
        }, "required": ["element_id"]},
    }},

    # ===== Touch Perform =====
    {"type": "function", "function": {
        "name": "touch_perform",
        "description": "Perform a sequence of touch actions.",
        "parameters": {"type": "object", "properties": {
            "actions": {"type": "array", "description": "List of touch actions"},
        }, "required": ["actions"]},
    }},
    {"type": "function", "function": {
        "name": "touch_multi_perform",
        "description": "Perform multiple touch action sequences simultaneously.",
        "parameters": {"type": "object", "properties": {
            "actions": {"type": "array", "description": "List of touch action sequences"},
        }, "required": ["actions"]},
    }},
    {"type": "function", "function": {
        "name": "w3c_actions",
        "description": "Perform W3C WebDriver actions.",
        "parameters": {"type": "object", "properties": {
            "actions": {"type": "object", "description": "W3C actions object"},
        }, "required": ["actions"]},
    }},
]


def create_handlers(executor):
    wda = executor.wda

    def tap(args):
        wda.tap(args["x"], args["y"])
        return "tapped"

    def swipe(args):
        wda.swipe(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "swiped"

    def pinch(args):
        wda.pinch(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "pinched"

    def rotate(args):
        wda.rotate(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "rotated"

    def double_tap(args):
        wda.double_tap(args["x"], args["y"])
        return "double tapped"

    def two_finger_tap(args):
        wda.two_finger_tap(args["x"], args["y"])
        return "two finger tapped"

    def touch_and_hold(args):
        wda.touch_and_hold(args["x"], args["y"], args.get("duration", 1.0))
        return "held"

    def scroll(args):
        wda.scroll(args.get("direction", "down"), args.get("distance", 0.5))
        return "scrolled"

    def drag(args):
        wda.drag(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "dragged"

    def press_and_drag(args):
        wda.press_and_drag(args["from_x"], args["from_y"], args["to_x"], args["to_y"], args.get("velocity", 800.0))
        return "pressed and dragged"

    def force_touch(args):
        wda.force_touch(args["x"], args["y"], args.get("pressure", 1.0), args.get("duration", 1.0))
        return "force touched"

    def tap_with_number_of_taps(args):
        wda.tap_with_number_of_taps(args["x"], args["y"], args.get("number_of_taps", 1), args.get("number_of_touches", 1))
        return "tapped"

    def swipe_element(args):
        wda.swipe_element(args["element_id"], args["direction"], args.get("velocity", 1.0))
        return "swiped"

    def pinch_element(args):
        wda.pinch_element(args["element_id"], args["scale"], args.get("velocity", 1.0))
        return "pinched"

    def rotate_element(args):
        wda.rotate_element(args["element_id"], args["rotation"], args.get("duration", 1.0))
        return "rotated"

    def double_tap_element(args):
        wda.double_tap_element(args["element_id"])
        return "double tapped"

    def two_finger_tap_element(args):
        wda.two_finger_tap_element(args["element_id"])
        return "two finger tapped"

    def touch_and_hold_element(args):
        wda.touch_and_hold_element(args["element_id"], args.get("duration", 1.0))
        return "held"

    def scroll_element(args):
        wda.scroll_element(args["element_id"], args.get("direction", "down"), args.get("distance", 0.5))
        return "scrolled"

    def scroll_to_element(args):
        wda.scroll_to_element(args["element_id"], args["target_element_id"])
        return "scrolled to element"

    def drag_element(args):
        wda.drag_element(args["element_id"], args["to_x"], args["to_y"], args.get("duration", 1.0))
        return "dragged"

    def press_and_drag_element(args):
        wda.press_and_drag_element(args["element_id"], args["to_x"], args["to_y"], args.get("velocity", 800.0))
        return "pressed and dragged"

    def force_touch_element(args):
        wda.force_touch_element(args["element_id"], args.get("pressure", 1.0), args.get("duration", 1.0))
        return "force touched"

    def tap_element_with_number_of_taps(args):
        wda.tap_element_with_number_of_taps(args["element_id"], args.get("number_of_taps", 1), args.get("number_of_touches", 1))
        return "tapped"

    def touch_perform(args):
        wda.touch_perform(args["actions"])
        return "performed"

    def touch_multi_perform(args):
        wda.touch_multi_perform(args["actions"])
        return "performed"

    def w3c_actions(args):
        wda.w3c_actions(args["actions"])
        return "performed"

    return {
        "tap": tap,
        "swipe": swipe,
        "pinch": pinch,
        "rotate": rotate,
        "double_tap": double_tap,
        "two_finger_tap": two_finger_tap,
        "touch_and_hold": touch_and_hold,
        "scroll": scroll,
        "drag": drag,
        "press_and_drag": press_and_drag,
        "force_touch": force_touch,
        "tap_with_number_of_taps": tap_with_number_of_taps,
        "swipe_element": swipe_element,
        "pinch_element": pinch_element,
        "rotate_element": rotate_element,
        "double_tap_element": double_tap_element,
        "two_finger_tap_element": two_finger_tap_element,
        "touch_and_hold_element": touch_and_hold_element,
        "scroll_element": scroll_element,
        "scroll_to_element": scroll_to_element,
        "drag_element": drag_element,
        "press_and_drag_element": press_and_drag_element,
        "force_touch_element": force_touch_element,
        "tap_element_with_number_of_taps": tap_element_with_number_of_taps,
        "touch_perform": touch_perform,
        "touch_multi_perform": touch_multi_perform,
        "w3c_actions": w3c_actions,
    }
