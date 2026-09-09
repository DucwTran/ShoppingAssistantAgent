import pytest

from app.core.config import settings
from app.graph.graph import build_graph
from app.graph.nodes.input_validation import InvalidQueryError, input_validation_node

REQUIRES_LIVE_KEYS = not settings.google_api_key or not settings.tavily_api_key
SKIP_REASON = "Requires real GOOGLE_API_KEY and TAVILY_API_KEY in .env"


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_input_validation_rejects_empty_query():
    with pytest.raises(InvalidQueryError):
        input_validation_node({"query": "   "})


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_laptop_ai_gaming():
    graph = build_graph()
    result = graph.invoke({"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"})
    recommendation = result["recommendation"]
    assert recommendation["product_name"]
    assert 0.0 <= recommendation["confidence"] <= 1.0


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_student_budget():
    graph = build_graph()
    result = graph.invoke({"query": "laptop mong nhe cho sinh vien duoi 15 trieu"})
    recommendation = result["recommendation"]
    assert recommendation["product_name"]
