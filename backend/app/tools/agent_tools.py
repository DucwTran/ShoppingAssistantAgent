from langchain_core.tools import tool

from app.guards.tool_argument_guard import call_tool
from app.guards.tool_result_guard import filter_valid_results
from app.schemas.comparison import CompareProductsArgs
from app.schemas.currency import ConvertCurrencyArgs
from app.schemas.knowledge_search import KnowledgeSearchArgs
from app.schemas.search import SearchRequest
from app.schemas.spec_score import ScoreProductSpecArgs
from app.tools.registry import TOOLS_BY_NAME


@tool(args_schema=SearchRequest)
def web_search(query: str, max_results: int = 5) -> list[dict] | str:
    """Search the web for current laptop product listings, prices and availability."""
    raw_results = call_tool(TOOLS_BY_NAME["web_search"], query=query, max_results=max_results)
    results, _ = filter_valid_results(raw_results)
    return results or "No results found for this query."


@tool(args_schema=KnowledgeSearchArgs)
def search_knowledge_base(query: str) -> list[dict] | str:
    """Search the internal hardware/domain knowledge base for conceptual questions (CPU/GPU/RAM/battery guides)."""
    results = call_tool(TOOLS_BY_NAME["search_knowledge_base"], query=query)
    return results or "No results found for this query."


@tool(args_schema=CompareProductsArgs)
def compare_products(products: list[dict]) -> dict:
    """Compare a list of normalized laptop products, identifying the cheapest and most expensive by price."""
    return call_tool(TOOLS_BY_NAME["compare_products"], products=products)


@tool(args_schema=ConvertCurrencyArgs)
def convert_currency(amount: float, from_currency: str, to_currency: str = "VND") -> float:
    """Convert an amount between currencies (VND, USD) using a fixed exchange rate."""
    return call_tool(TOOLS_BY_NAME["convert_currency"], amount=amount, from_currency=from_currency, to_currency=to_currency)


@tool(args_schema=ScoreProductSpecArgs)
def score_product_spec(product: dict, budget: float | None = None) -> dict:
    """Score how well one product fits the budget and how complete its spec data is (0-1, higher is better)."""
    return call_tool(TOOLS_BY_NAME["score_product_spec"], product=product, budget=budget)


RESEARCH_TOOLS = [web_search, search_knowledge_base]
RECOMMEND_TOOLS = [compare_products, convert_currency, score_product_spec]
