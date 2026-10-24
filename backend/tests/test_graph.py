import uuid

import pytest
from langgraph.types import Command

from app.core.config import settings
from app.graph.graph import _route_after_feedback, _route_after_human_approval, _route_after_understand, build_graph
from app.graph.nodes.input_validation import input_validation_node
from app.guards.input_guard import InvalidQueryError



def _thread_config():
    return {"configurable": {"thread_id": str(uuid.uuid4())}}


# --- routing --------------------------------------------------------------------------------------


def test_build_graph_includes_all_nodes():
    node_names = set(build_graph().get_graph().nodes)
    assert {"understand", "research_agent", "extract_products", "recommend", "evaluator",
            "request_approval", "human_approval", "feedback_router", "record_turn"} <= node_names


def test_route_after_understand():
    assert _route_after_understand({"intent": "shopping"}) == "research_agent"
    assert _route_after_understand({"intent": "general"}) == "record_turn"


def test_route_after_human_approval():
    assert _route_after_human_approval({"human_approval": True}) == "record_turn"
    assert _route_after_human_approval({"human_approval": False}) == "feedback_router"
    capped = {"human_approval": False, "human_rejection_count": settings.max_human_rejections}
    assert _route_after_human_approval(capped) == "record_turn"


def test_route_after_feedback():
    assert _route_after_feedback({"research_hint": "laptop AMD"}) == "research_agent"
    assert _route_after_feedback({"research_hint": None}) == "recommend"


def test_input_validation_rejects_empty_query():
    with pytest.raises(InvalidQueryError):
        input_validation_node({"query": "   "})


# --- full graph, offline (fake LLM + fake agent loop) ---------------------------------------------


def _events(graph, graph_input, config) -> list[str]:
    return [event["event"] for event in graph.stream(graph_input, config, stream_mode="custom")]


def test_approval_events_are_emitted_once_across_pause_and_resume(fake_pipeline):
    # Resuming re-runs the interrupted node from its first line, so anything placed before
    # interrupt() would run - and emit - a second time.
    graph, config = build_graph(), _thread_config()
    events = _events(graph, {"query": "laptop gaming dưới 25 triệu"}, config)
    events += _events(graph, Command(resume={"approved": True, "feedback": None}), config)

    assert events.count("hitl_required") == 1
    assert events.count("hitl_resolved") == 1


def test_offline_flow_grounds_products_and_pauses_for_approval(fake_pipeline):
    graph, config = build_graph(), _thread_config()
    result = graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)

    assert "__interrupt__" in result
    state = graph.get_state(config).values
    names = [p["name"] for p in state["products"]]
    assert names == ["Acer Nitro V 15", "ASUS TUF A15"]  # hallucinated product dropped
    assert state["products"][0]["price"] == 22_990_000  # "22.990.000" parsed

    recommendation = result["__interrupt__"][0].value["recommendation"]
    assert recommendation["product_name"] == "Acer Nitro V 15"
    assert recommendation["url"] == "https://fptshop.com.vn/acer-nitro-v"
    assert 0.0 <= result["__interrupt__"][0].value["quality_score"] <= 1.0


def test_offline_general_chat_ends_without_research(fake_pipeline):
    fake_pipeline.is_shopping = False
    result = build_graph().invoke({"query": "hello"}, _thread_config())
    assert result["general_reply"] == "Xin chào!"
    assert "research_agent" not in fake_pipeline.calls


def test_offline_reject_needing_new_products_researches_again(fake_pipeline):
    graph, config = build_graph(), _thread_config()
    graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)

    fake_pipeline.needs_new_products = True
    result = graph.invoke(Command(resume={"approved": False, "feedback": "prefer AMD GPU"}), config)

    assert "__interrupt__" in result
    assert fake_pipeline.calls.count("research_agent") == 2
    assert graph.get_state(config).values["research_hint"] == "laptop AMD"


def test_offline_reject_satisfiable_from_candidates_skips_research(fake_pipeline):
    graph, config = build_graph(), _thread_config()
    graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)

    fake_pipeline.product_id = 1
    result = graph.invoke(Command(resume={"approved": False, "feedback": "the ASUS instead"}), config)

    assert fake_pipeline.calls.count("research_agent") == 1
    recommendation = result["__interrupt__"][0].value["recommendation"]
    assert recommendation["product_name"] == "ASUS TUF A15"
    # 26.49M > 25M budget: the guard must disclose it even though the model listed no tradeoffs
    assert any("budget" in t for t in recommendation["tradeoffs"])


def test_offline_second_rejection_keeps_the_first_feedback(fake_pipeline):
    graph, config = build_graph(), _thread_config()
    graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)

    fake_pipeline.needs_new_products = True
    graph.invoke(Command(resume={"approved": False, "feedback": "prefer AMD GPU"}), config)
    fake_pipeline.needs_new_products = False
    graph.invoke(Command(resume={"approved": False, "feedback": "cheaper"}), config)

    expected = ["prefer AMD GPU", "cheaper"]
    assert fake_pipeline.payloads["FeedbackDecision"]["feedback"] == expected
    assert fake_pipeline.payloads["RecommendationChoice"]["human_feedback"] == expected


def test_offline_follow_up_keeps_history_and_resets_the_turn(fake_pipeline):
    graph, config = build_graph(), _thread_config()
    graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)
    graph.invoke(Command(resume={"approved": False, "feedback": "the ASUS instead"}), config)
    graph.invoke(Command(resume={"approved": True, "feedback": None}), config)

    fake_pipeline.standalone_query = "laptop gaming rẻ hơn Acer Nitro V 15"
    result = graph.invoke({"query": "còn máy nào rẻ hơn không?"}, config)

    state = graph.get_state(config).values
    assert "__interrupt__" in result
    assert [turn["question"] for turn in state["history"]] == ["laptop gaming dưới 25 triệu"]
    assert state["history"][0]["answer"].startswith("Recommended Acer Nitro V 15")
    # The previous turn's rejection and feedback do not carry over
    assert state["human_rejection_count"] == 0 and state["human_feedback"] == []
    # understand sees the history; the rest of the pipeline reads the resolved question
    assert fake_pipeline.payloads["QueryUnderstanding"]["message"] == "còn máy nào rẻ hơn không?"
    assert fake_pipeline.payloads["RecommendationChoice"]["question"] == "laptop gaming rẻ hơn Acer Nitro V 15"


def test_offline_history_keeps_the_most_recent_turns(fake_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "max_history_turns", 2)
    fake_pipeline.is_shopping = False
    graph, config = build_graph(), _thread_config()
    for query in ("hi", "hello", "xin chào"):
        graph.invoke({"query": query}, config)

    assert [turn["question"] for turn in graph.get_state(config).values["history"]] == ["hello", "xin chào"]


def test_offline_empty_research_is_reported_not_guessed(fake_pipeline, monkeypatch):
    from app.graph.nodes import research_agent

    fake_pipeline.web_results, fake_pipeline.docs = [], []
    monkeypatch.setattr(research_agent, "_fallback_research", lambda state: ([], []))
    fake_pipeline.product_id = None

    graph, config = build_graph(), _thread_config()
    result = graph.invoke({"query": "laptop gaming dưới 25 triệu"}, config)

    state = graph.get_state(config).values
    assert state["research_status"] == "empty"
    assert state["products"] == []
    assert result["__interrupt__"][0].value["recommendation"]["product_name"] == "N/A"


def test_offline_invalid_product_id_is_rejected(fake_pipeline):
    fake_pipeline.product_id = 99
    with pytest.raises(ValueError):
        build_graph().invoke({"query": "laptop gaming dưới 25 triệu"}, _thread_config())


# --- live (real Gemini + Tavily, run with `pytest -m live`) -----------------------------------


def _assert_grounded(state: dict) -> None:
    recommendation = state["recommendation"]
    assert state["products"], "research should produce at least one grounded product"
    web_urls = {r["url"] for r in state["web_results"]}
    assert all(p["source_url"] in web_urls for p in state["products"])
    if recommendation["product_name"] != "N/A":
        assert recommendation["url"] in web_urls
        budget = state.get("budget")
        if budget and recommendation["price"] and recommendation["price"] > budget:
            assert any("budget" in t.lower() or "ngân sách" in t.lower() for t in recommendation["tradeoffs"])


@pytest.mark.live
def test_live_shopping_query_is_grounded():
    graph, config = build_graph(), _thread_config()
    result = graph.invoke({"query": "laptop dưới 25 triệu cho lập trình AI và gaming"}, config)
    assert "__interrupt__" in result
    _assert_grounded(graph.get_state(config).values)


@pytest.mark.live
def test_live_technical_question_uses_knowledge():
    graph, config = build_graph(), _thread_config()
    result = graph.invoke({"query": "RTX 4060 có đủ mạnh cho AI development không?"}, config)
    assert result["__interrupt__"][0].value["recommendation"]["why_it_fits"]
    assert graph.get_state(config).values["retrieved_docs"]


@pytest.mark.live
def test_live_reject_then_approve():
    graph, config = build_graph(), _thread_config()
    graph.invoke({"query": "laptop dưới 25 triệu cho lập trình AI và gaming"}, config)

    result = graph.invoke(Command(resume={"approved": False, "feedback": "prefer AMD GPU"}), config)
    assert "__interrupt__" in result
    _assert_grounded(graph.get_state(config).values)

    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    assert result["human_approval"] is True
