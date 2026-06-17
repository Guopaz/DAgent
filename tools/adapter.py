"""Bridge existing WDA tool schemas + handlers into HelloAgents Tool protocol."""

from typing import Any, Callable, Dict, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus
from hello_agents.tools.errors import ToolErrorCode


def _schema_prop_to_parameter(name: str, prop: dict, required: bool) -> ToolParameter:
    return ToolParameter(
        name=name,
        type=prop.get("type", "string"),
        description=prop.get("description", ""),
        required=required,
        default=None,
    )


class WDAFunctionTool(Tool):
    """Wraps a single legacy tool (schema dict + handler callable) as a HelloAgents Tool."""

    def __init__(self, schema: dict, handler: Callable[[dict], Any]):
        func_def = schema["function"]
        super().__init__(
            name=func_def["name"],
            description=func_def["description"],
        )
        self._handler = handler
        params_schema = func_def.get("parameters", {})
        required_set = set(params_schema.get("required", []))
        self._parameters: List[ToolParameter] = [
            _schema_prop_to_parameter(n, p, n in required_set)
            for n, p in params_schema.get("properties", {}).items()
        ]

    def get_parameters(self) -> List[ToolParameter]:
        return self._parameters

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        try:
            result = self._handler(parameters)
            if result is None:
                return ToolResponse.success(text="ok")
            return ToolResponse.success(text=str(result), data={"output": result})
        except Exception as exc:
            return ToolResponse.error(
                code=ToolErrorCode.EXECUTION_ERROR,
                message=f"{type(exc).__name__}: {exc}",
            )


def build_wda_tools(
    wda,
    tool_modules: list | None = None,
) -> list[WDAFunctionTool]:
    """Build WDAFunctionTool instances from legacy tool modules."""
    if tool_modules is None:
        return []

    class _ExecutorShim:
        def __init__(self, wda):
            self.wda = wda

    executor = _ExecutorShim(wda)

    tools: list[WDAFunctionTool] = []
    for module in tool_modules:
        handlers = module.create_handlers(executor)
        for schema in module.TOOL_SCHEMAS:
            func_name = schema["function"]["name"]
            handler = handlers.get(func_name)
            if handler is None:
                continue
            tools.append(WDAFunctionTool(schema, handler))
    return tools
