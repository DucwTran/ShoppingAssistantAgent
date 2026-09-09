from typing import Any

from pydantic import ValidationError

from app.tools.base import RegisteredTool


class ToolArgumentError(ValueError):
    pass


def call_tool(tool: RegisteredTool, **kwargs: Any) -> Any:
    try:
        return tool.run(**kwargs)
    except ValidationError as exc:
        raise ToolArgumentError(f"Invalid arguments for tool '{tool.name}': {exc}") from exc
