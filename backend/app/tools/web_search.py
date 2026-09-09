from langchain_tavily import TavilySearch

from app.core.config import settings
from app.schemas.search import SearchRequest
from app.tools.base import RegisteredTool


def _search(query: str, max_results: int = 5) -> list[dict]:
    tool = TavilySearch(tavily_api_key=settings.tavily_api_key, max_results=max_results)
    result = tool.invoke({"query": query})
    return result.get("results", []) if isinstance(result, dict) else result


web_search_tool = RegisteredTool(
    name="web_search",
    description="Search the web for current product information via Tavily.",
    args_schema=SearchRequest,
    func=_search,
)
