from app.tools.base import RegisteredTool
from app.tools.web_search import web_search_tool

ALL_TOOLS: list[RegisteredTool] = [web_search_tool]

TOOLS_BY_NAME: dict[str, RegisteredTool] = {tool.name: tool for tool in ALL_TOOLS}
