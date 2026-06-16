"""Element tools: finding elements, querying properties, and interacting with them."""
from __future__ import annotations


TOOL_SCHEMAS = [
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
        "description": "Check whether an element is currently displayed on screen.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "is_element_enabled",
        "description": "Check whether an element is currently enabled (interactive).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "is_element_selected",
        "description": "Check whether an element is currently selected (e.g. checkbox, tab).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_element_name",
        "description": "Get the name/label of an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "get_element_rect",
        "description": "Get the bounding rectangle (position and size) of an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "is_element_accessible",
        "description": "Check whether an element is accessible.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "is_element_accessibility_container",
        "description": "Check whether an element acts as an accessibility container.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "is_element_focused",
        "description": "Check whether an element currently has focus.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},

    # ===== Element Interaction =====
    {"type": "function", "function": {
        "name": "click_element",
        "description": "Click (tap) on an element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "click_element_relative",
        "description": "Click on a relative position within an element (x,y in 0..1).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "x": {"type": "number", "description": "Relative x position (0..1, default 0.5)"},
            "y": {"type": "number", "description": "Relative y position (0..1, default 0.5)"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "tap_element",
        "description": "Tap on an element (synonym for click_element).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "send_keys",
        "description": "Send text to an element (types into a text field).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "text": {"type": "string", "description": "Text to send"},
        }, "required": ["element_id", "text"]},
    }},
    {"type": "function", "function": {
        "name": "keyboard_input",
        "description": "Send keyboard input to an element (alternative to send_keys).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "text": {"type": "string", "description": "Text to input"},
        }, "required": ["element_id", "text"]},
    }},
    {"type": "function", "function": {
        "name": "clear_element",
        "description": "Clear the text content of a text field element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "focus_element",
        "description": "Focus an element (make it the active element).",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
        }, "required": ["element_id"]},
    }},
    {"type": "function", "function": {
        "name": "select_pickerwheel",
        "description": "Select a value from a picker wheel element.",
        "parameters": {"type": "object", "properties": {
            "element_id": {"type": "string", "description": "Element ID"},
            "order": {"type": "string", "description": "Selection order: next or previous"},
            "offset": {"type": "integer", "description": "Offset (default 1)"},
        }, "required": ["element_id", "order"]},
    }},
]


def create_handlers(executor):
    wda = executor.wda

    def find_element(args):
        eid = wda.find_element(args["using"], args["value"])
        return {"element_id": eid} if eid else None

    def find_elements(args):
        return wda.find_elements(args["using"], args["value"])

    def find_element_from_element(args):
        eid = wda.find_element_from_element(args["element_id"], args["using"], args["value"])
        return {"element_id": eid} if eid else None

    def find_elements_from_element(args):
        return wda.find_elements_from_element(args["element_id"], args["using"], args["value"])

    def get_active_element(args):
        eid = wda.get_active_element()
        return {"element_id": eid} if eid else None

    def get_visible_cells(args):
        return wda.get_visible_cells(args["element_id"])

    def get_element_text(args):
        return wda.get_element_text(args["element_id"])

    def get_element_attribute(args):
        return wda.get_element_attribute(args["element_id"], args["name"])

    def is_element_displayed(args):
        return wda.is_element_displayed(args["element_id"])

    def is_element_enabled(args):
        return wda.is_element_enabled(args["element_id"])

    def is_element_selected(args):
        return wda.is_element_selected(args["element_id"])

    def get_element_name(args):
        return wda.get_element_name(args["element_id"])

    def get_element_rect(args):
        return wda.get_element_rect(args["element_id"])

    def is_element_accessible(args):
        return wda.is_element_accessible(args["element_id"])

    def is_element_accessibility_container(args):
        return wda.is_element_accessibility_container(args["element_id"])

    def is_element_focused(args):
        return wda.is_element_focused(args["element_id"])

    def click_element(args):
        wda.click_element(args["element_id"])
        return "clicked"

    def click_element_relative(args):
        wda.click_element_relative(args["element_id"], args.get("x", 0.5), args.get("y", 0.5))
        return "clicked"

    def tap_element(args):
        wda.tap_element(args["element_id"])
        return "tapped"

    def send_keys(args):
        wda.send_keys(args["element_id"], args["text"])
        return "sent"

    def keyboard_input(args):
        wda.keyboard_input(args["element_id"], args["text"])
        return "input sent"

    def clear_element(args):
        wda.clear_element(args["element_id"])
        return "cleared"

    def focus_element(args):
        wda.focus_element(args["element_id"])
        return "focused"

    def select_pickerwheel(args):
        wda.select_pickerwheel(args["element_id"], args["order"], args.get("offset", 1))
        return "selected"

    return {
        "find_element": find_element,
        "find_elements": find_elements,
        "find_element_from_element": find_element_from_element,
        "find_elements_from_element": find_elements_from_element,
        "get_active_element": get_active_element,
        "get_visible_cells": get_visible_cells,
        "get_element_text": get_element_text,
        "get_element_attribute": get_element_attribute,
        "is_element_displayed": is_element_displayed,
        "is_element_enabled": is_element_enabled,
        "is_element_selected": is_element_selected,
        "get_element_name": get_element_name,
        "get_element_rect": get_element_rect,
        "is_element_accessible": is_element_accessible,
        "is_element_accessibility_container": is_element_accessibility_container,
        "is_element_focused": is_element_focused,
        "click_element": click_element,
        "click_element_relative": click_element_relative,
        "tap_element": tap_element,
        "send_keys": send_keys,
        "keyboard_input": keyboard_input,
        "clear_element": clear_element,
        "focus_element": focus_element,
        "select_pickerwheel": select_pickerwheel,
    }
