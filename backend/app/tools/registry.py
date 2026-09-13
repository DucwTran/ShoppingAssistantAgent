from app.tools.base import RegisteredTool
from app.tools.compare import compare_products_tool
from app.tools.currency import convert_currency_tool
from app.tools.knowledge_base import search_knowledge_base_tool
from app.tools.spec_score import score_product_spec_tool
from app.tools.web_search import web_search_tool

ALL_TOOLS: list[RegisteredTool] = [
    web_search_tool,
    compare_products_tool,
    convert_currency_tool,
    search_knowledge_base_tool,
    score_product_spec_tool,
]

TOOLS_BY_NAME: dict[str, RegisteredTool] = {tool.name: tool for tool in ALL_TOOLS}
