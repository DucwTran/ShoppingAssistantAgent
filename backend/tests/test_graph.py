import pytest

from langgraph.graph import END

from app.core.config import settings
from app.graph.graph import _route_after_evaluator, _route_by_source_flags, build_graph
from app.graph.nodes.input_validation import input_validation_node
from app.guards.input_guard import InvalidQueryError

REQUIRES_LIVE_KEYS = (
    not settings.google_api_key or not settings.tavily_api_key or not settings.groq_api_key
)
SKIP_REASON = "Requires real GOOGLE_API_KEY, TAVILY_API_KEY and GROQ_API_KEY in .env"


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_build_graph_includes_evaluation_and_reflection_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes)
    assert "evaluator" in node_names
    assert "reflection" in node_names


def test_route_by_source_flags_web_only():
    assert _route_by_source_flags({"use_web": True, "use_rag": False}) == ["web_search"]


def test_route_by_source_flags_rag_only():
    assert _route_by_source_flags({"use_web": False, "use_rag": True}) == ["rag"]


def test_route_by_source_flags_both():
    branches = _route_by_source_flags({"use_web": True, "use_rag": True})
    assert set(branches) == {"web_search", "rag"}


def test_route_by_source_flags_defaults_to_web_search():
    assert _route_by_source_flags({}) == ["web_search"]


def test_route_after_evaluator_proceeds_when_score_meets_threshold():
    state = {"quality_score": settings.quality_threshold, "reflection_count": 0}
    assert _route_after_evaluator(state) == END


def test_route_after_evaluator_reflects_when_below_threshold_and_attempts_remain():
    state = {"quality_score": 0.1, "reflection_count": 0}
    assert _route_after_evaluator(state) == "reflection"


def test_route_after_evaluator_degrades_when_reflection_budget_exhausted():
    state = {"quality_score": 0.1, "reflection_count": settings.max_reflections}
    assert _route_after_evaluator(state) == END


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


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_rag_only_technical_question():
    graph = build_graph()
    result = graph.invoke({"query": "laptop RTX 4060 co du manh cho AI development khong?"})
    assert result.get("retrieved_docs")
    recommendation = result["recommendation"]
    assert recommendation["why_it_fits"]


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_evaluates_and_bounds_reflection():
    graph = build_graph()
    result = graph.invoke(
        {"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"},
        config={"recursion_limit": 40},
    )
    assert 0.0 <= result["quality_score"] <= 1.0
    assert result.get("reflection_count", 0) <= settings.max_reflections
