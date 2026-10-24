"""Offline doubles for the graph: every LLM call and the research agent loop are replaced, the rest runs for real."""

import json
from dataclasses import dataclass, field

import pytest
from langchain_core.messages import ToolMessage

from app.core.config import settings
from app.graph.nodes import extract_products, feedback_router, recommend, research_agent, understand
from app.schemas.feedback import FeedbackDecision
from app.schemas.product import Product
from app.schemas.recommendation import RecommendationChoice
from app.schemas.research import ProductExtraction
from app.schemas.understanding import QueryUnderstanding
from app.tools import price_lookup
from evals import judge
from evals.judge import PurposeJudgement

WEB_RESULTS = [
    {"title": "Laptop Acer Nitro V 15 RTX 4050", "url": "https://fptshop.com.vn/acer-nitro-v",
     "content": "i5-13420H, 16GB, SSD 512GB - 22.990.000đ"},
    {"title": "Laptop ASUS TUF A15 RTX 4060", "url": "https://gearvn.com/asus-tuf-a15",
     "content": "Ryzen 7 7735HS, 16GB, SSD 512GB - 26.490.000đ"},
]
KNOWLEDGE_DOCS = [{"text": "RTX 4060 has 8GB VRAM, fine for small local models.", "source": "gpu_guide.md"}]


def _extracted_products() -> list[Product]:
    return [
        Product(name="Acer Nitro V 15", price="22.990.000", cpu="i5-13420H", gpu="RTX 4050", ram="16GB",
                storage="512GB", source_url=WEB_RESULTS[0]["url"]),
        Product(name="ASUS TUF A15", price=26_490_000, cpu="Ryzen 7 7735HS", gpu="RTX 4060", ram="16GB",
                storage="512GB", source_url=WEB_RESULTS[1]["url"]),
        # Not tied to any retrieved result - the grounding guard must drop it.
        Product(name="Hallucinated Laptop", price=1, source_url="https://made-up.example"),
    ]


@dataclass
class FakePipeline:
    is_shopping: bool = True
    web_results: list[dict] = field(default_factory=lambda: list(WEB_RESULTS))
    docs: list[dict] = field(default_factory=lambda: list(KNOWLEDGE_DOCS))
    product_id: int | None = 0
    needs_new_products: bool = False
    calls: list[str] = field(default_factory=list)
    # schema name -> error raised once, the next time that schema is requested
    failures: dict[str, Exception] = field(default_factory=dict)
    # schema name -> JSON payload of the latest request for it
    payloads: dict[str, dict] = field(default_factory=dict)
    # schema name -> thinking level of the latest request for it
    thinking_levels: dict[str, str | None] = field(default_factory=dict)
    # Results returned by the second search for missing prices
    price_lookup_results: list[dict] = field(default_factory=list)
    # Overrides what extraction returns; None uses _extracted_products()
    extracted: list[Product] | None = None
    # What understand rewrites the message to; None leaves the message as it is
    standalone_query: str | None = None

    def structured(self, schema, messages, check=None, max_retries=2, thinking_level=None):
        self.calls.append(schema.__name__)
        self.thinking_levels[schema.__name__] = thinking_level
        human = messages[-1][1]
        if human.startswith("{"):
            self.payloads[schema.__name__] = json.loads(human)
        if schema.__name__ in self.failures:
            raise self.failures.pop(schema.__name__)
        if schema is QueryUnderstanding:
            result = QueryUnderstanding(
                is_shopping_related=self.is_shopping,
                standalone_query=self.standalone_query,
                reply=None if self.is_shopping else "Xin chào!",
                budget=25_000_000 if self.is_shopping else None,
                purpose=["gaming"] if self.is_shopping else [],
            )
        elif schema is ProductExtraction:
            result = ProductExtraction(products=self.extracted if self.extracted is not None else _extracted_products())
        elif schema is RecommendationChoice:
            result = RecommendationChoice(
                product_id=self.product_id, alternative_id=None, why_it_fits=["fits"], tradeoffs=[], confidence=0.8
            )
        elif schema is PurposeJudgement:
            result = PurposeJudgement(purpose_fit=0.9, feedback="Solid.")
        elif schema is FeedbackDecision:
            result = FeedbackDecision(
                needs_new_products=self.needs_new_products,
                research_hint="laptop AMD" if self.needs_new_products else None,
            )
        else:
            raise AssertionError(f"unexpected schema {schema}")
        if check:
            check(result)
        return result

    def run_agent(self, state):
        self.calls.append("research_agent")
        return [
            ToolMessage(content="...", artifact=self.web_results, name="web_search", tool_call_id="1"),
            ToolMessage(content="...", artifact=self.docs, name="search_knowledge_base", tool_call_id="2"),
        ]


def pytest_collection_modifyitems(config, items):
    """Live tests are opt-in (`pytest -m live`); when requested without the keys they need, skip them."""
    missing = settings.missing_required_keys()
    if not missing:
        return
    skip = pytest.mark.skip(reason=f"Live test: set {', '.join(missing)} in .env")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def fake_pipeline(monkeypatch) -> FakePipeline:
    fake = FakePipeline()
    # judge: the eval harness calls it on finished runs, so offline eval tests must not reach the API either
    for module in (understand, extract_products, recommend, feedback_router, judge):
        monkeypatch.setattr(module, "invoke_structured", fake.structured)
    monkeypatch.setattr(research_agent, "_run_agent", fake.run_agent)
    monkeypatch.setattr(price_lookup, "search_web", lambda query, max_results: fake.price_lookup_results)
    return fake
