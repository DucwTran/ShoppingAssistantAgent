import uuid

import pytest

from langgraph.graph import END
from langgraph.types import Command

from app.core.config import settings
from app.graph.graph import (
    _route_after_evaluator,
    _route_after_human_approval,
    _route_after_intent,
    build_graph,
)
from app.graph.nodes.input_validation import input_validation_node
from app.guards.input_guard import InvalidQueryError

REQUIRES_LIVE_KEYS = not settings.tavily_api_key
SKIP_REASON = "Requires real TAVILY_API_KEY in .env (chat/embeddings run locally via Ollama)"


def _thread_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


def _run_to_approval(graph, query: str):
    config = _thread_config()
    result = graph.invoke({"query": query}, config)
    assert "__interrupt__" in result
    return graph, config, result


def test_build_graph_compiles():
    graph = build_graph()
    assert graph is not None


def test_build_graph_includes_evaluation_and_reflection_nodes():
    graph = build_graph()
    node_names = set(graph.get_graph().nodes)
    assert "evaluator" in node_names
    assert "reflection" in node_names
    assert "human_approval" in node_names
    assert "intent" in node_names
    assert "research_agent" in node_names


def test_route_after_intent_shopping_goes_to_metadata():
    assert _route_after_intent({"intent": "shopping"}) == "metadata"


def test_route_after_intent_general_ends():
    assert _route_after_intent({"intent": "general"}) == END


def test_route_after_evaluator_proceeds_when_score_meets_threshold():
    state = {"quality_score": settings.quality_threshold, "reflection_count": 0}
    assert _route_after_evaluator(state) == "human_approval"


def test_route_after_evaluator_reflects_when_below_threshold_and_attempts_remain():
    state = {"quality_score": 0.1, "reflection_count": 0}
    assert _route_after_evaluator(state) == "reflection"


def test_route_after_evaluator_degrades_when_reflection_budget_exhausted():
    state = {"quality_score": 0.1, "reflection_count": settings.max_reflections}
    assert _route_after_evaluator(state) == "human_approval"


def test_route_after_human_approval_approved_ends():
    assert _route_after_human_approval({"human_approval": True}) == END


def test_route_after_human_approval_rejected_returns_to_recommend():
    assert _route_after_human_approval({"human_approval": False}) == "recommend"


def test_input_validation_rejects_empty_query():
    with pytest.raises(InvalidQueryError):
        input_validation_node({"query": "   "})


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_laptop_ai_gaming():
    graph, config, paused = _run_to_approval(build_graph(), "laptop duoi 25 trieu cho lap trinh AI va gaming")
    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    recommendation = result["recommendation"]
    assert recommendation["product_name"]
    assert 0.0 <= recommendation["confidence"] <= 1.0


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_student_budget():
    graph, config, paused = _run_to_approval(build_graph(), "laptop mong nhe cho sinh vien duoi 15 trieu")
    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    recommendation = result["recommendation"]
    assert recommendation["product_name"]


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_rag_only_technical_question():
    graph, config, paused = _run_to_approval(
        build_graph(), "laptop RTX 4060 co du manh cho AI development khong?"
    )
    assert paused["__interrupt__"][0].value["recommendation"]["why_it_fits"]
    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    assert result.get("retrieved_docs")
    assert result["recommendation"]["why_it_fits"]


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_evaluates_and_bounds_reflection():
    graph, config, paused = _run_to_approval(
        build_graph(), "laptop duoi 25 trieu cho lap trinh AI va gaming"
    )
    interrupt_payload = paused["__interrupt__"][0].value
    assert 0.0 <= interrupt_payload["quality_score"] <= 1.0
    assert interrupt_payload["reflection_count"] <= settings.max_reflections

    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    assert 0.0 <= result["quality_score"] <= 1.0
    assert result.get("reflection_count", 0) <= settings.max_reflections


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_graph_end_to_end_hitl_reject_then_approve():
    graph, config, paused = _run_to_approval(build_graph(), "laptop duoi 25 trieu cho lap trinh AI va gaming")

    result = graph.invoke(Command(resume={"approved": False, "feedback": "prefer AMD GPU"}), config)
    assert "__interrupt__" in result, "rejecting should route back through recommend/evaluator to another approval"

    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    assert "__interrupt__" not in result
    assert result["human_approval"] is True
    assert result["recommendation"]["product_name"]
