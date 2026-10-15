import re
from functools import lru_cache

from langchain_tavily import TavilySearch

from app.core.config import settings

# A thousands-grouped amount with a VND marker, e.g. "19.290.000đ", "27,490,000 VNĐ"
_PRICE_PATTERN = re.compile(r"\d{1,3}(?:[.,]\d{3}){2}\s*(?:đ|₫|VNĐ|VND)", re.IGNORECASE)
_PRICE_LINES_CHARS = 1200


@lru_cache(maxsize=1)
def _client() -> TavilySearch:
    return TavilySearch(
        tavily_api_key=settings.tavily_api_key,
        max_results=settings.web_search_max_results,
        search_depth="advanced",
        include_raw_content="text",
        # Only pages updated in the last year - older listicles carry outdated models and prices
        time_range="year",
    )


def _condense(result: dict) -> dict:
    """Replace the full page text with just its price-bearing lines, appended to the snippet.

    Tavily's snippet rarely includes prices, while retailer pages list "model ... specs ... price" on one
    line. Keeping only those lines gives extraction the data it needs at a bounded size, and keeps whole
    pages out of graph state.
    """
    raw = result.pop("raw_content", None) or ""
    price_lines = [" ".join(line.split()) for line in raw.splitlines() if _PRICE_PATTERN.search(line)]
    if price_lines:
        listing = "\n".join(price_lines)[:_PRICE_LINES_CHARS]
        result["content"] = f"{result.get('content') or ''}\nPrice listings on page:\n{listing}"
    return result


def _run(query: str, include_domains: list[str] | None) -> list[dict]:
    result = _client().invoke({"query": query, "include_domains": include_domains})
    results = result.get("results", []) if isinstance(result, dict) else result
    return [_condense(r) for r in results]


def search_web(query: str, max_results: int = 5) -> list[dict]:
    # Retailer domains carry the price/spec data the pipeline needs; fall back to the open web
    # rather than return nothing when they have no match (e.g. an English or niche query).
    results = _run(query, settings.web_search_domains or None)
    if not results and settings.web_search_domains:
        results = _run(query, None)
    return results[:max_results]
