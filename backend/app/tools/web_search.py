import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from functools import lru_cache

from langchain_tavily import TavilySearch

from app.core.config import settings

# Price lookups run up to 6 searches at once on top of the agent's own
_search_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="web-search")

# A thousands-grouped amount with a VND marker, e.g. "19.290.000đ", "27,490,000 VNĐ"
PRICE_PATTERN = re.compile(r"\d{1,3}(?:[.,]\d{3}){2}\s*(?:đ|₫|VNĐ|VND)", re.IGNORECASE)
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
    """Replace the full page text with just its price-bearing lines, kept in `price_listing`.

    Tavily's snippet rarely includes prices, while retailer pages list "model ... specs ... price" on one
    line. Keeping only those lines gives extraction the data it needs at a bounded size, and keeps whole
    pages out of graph state. They stay out of `content` so that trimming a long snippet cannot cut them.
    """
    raw = result.pop("raw_content", None) or ""
    price_lines = [" ".join(line.split()) for line in raw.splitlines() if PRICE_PATTERN.search(line)]
    if price_lines:
        result["price_listing"] = "\n".join(price_lines)[:_PRICE_LINES_CHARS]
    return result


def page_text(result: dict) -> str:
    """Everything a search result says about its page: what prices and specs are verified against."""
    return f"{result.get('title') or ''}\n{result.get('content') or ''}\n{result.get('price_listing') or ''}"


def _run(query: str, include_domains: list[str] | None) -> list[dict]:
    # langchain-tavily posts without a timeout, so a stalled connection would hold the request forever.
    # Waiting is bounded here; the abandoned call finishes or fails in its pool thread.
    future = _search_pool.submit(_client().invoke, {"query": query, "include_domains": include_domains})
    try:
        result = future.result(timeout=settings.web_search_timeout_seconds)
    except FutureTimeout:
        raise TimeoutError(f"Web search did not answer within {settings.web_search_timeout_seconds:.0f} s") from None
    results = result.get("results", []) if isinstance(result, dict) else result
    return [_condense(r) for r in results]


def search_web(query: str, max_results: int = 5) -> list[dict]:
    # Retailer domains carry the price/spec data the pipeline needs; fall back to the open web
    # rather than return nothing when they have no match (e.g. an English or niche query).
    results = _run(query, settings.web_search_domains or None)
    if not results and settings.web_search_domains:
        results = _run(query, None)
    return results[:max_results]
