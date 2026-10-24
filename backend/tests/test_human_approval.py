from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from langgraph.checkpoint.memory import InMemorySaver
from app.graph.nodes.human_approval import _build_approval_payload, human_approval_node
from app.graph.state import ShoppingState


def test_build_approval_payload_carries_the_recommendation():
    payload = _build_approval_payload({"recommendation": {"product_name": "Laptop X"}, "products": [{"name": "Y"}]})
    assert payload == {"recommendation": {"product_name": "Laptop X"}}


def _build_approval_only_graph():
    graph = StateGraph(ShoppingState)
    graph.add_node("human_approval", human_approval_node)
    graph.add_edge(START, "human_approval")
    graph.add_edge("human_approval", END)
    return graph.compile(checkpointer=InMemorySaver())


def test_human_approval_interrupts_then_resolves_on_approve():
    graph = _build_approval_only_graph()
    config = {"configurable": {"thread_id": "test-approve"}}

    result = graph.invoke({"recommendation": {"product_name": "Laptop X"}}, config)
    assert "__interrupt__" in result
    assert result["__interrupt__"][0].value["recommendation"]["product_name"] == "Laptop X"
    assert graph.get_state(config).next == ("human_approval",)

    result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
    assert "__interrupt__" not in result
    assert result["human_approval"] is True
    assert result["human_feedback"] == []


def test_human_approval_resolves_on_reject_with_feedback():
    graph = _build_approval_only_graph()
    config = {"configurable": {"thread_id": "test-reject"}}

    graph.invoke({"recommendation": {"product_name": "Laptop X"}}, config)
    result = graph.invoke(Command(resume={"approved": False, "feedback": "cheaper option"}), config)

    assert result["human_approval"] is False
    assert result["human_feedback"] == ["cheaper option"]


def test_human_approval_keeps_earlier_feedback_and_skips_blank():
    graph = _build_approval_only_graph()
    config = {"configurable": {"thread_id": "test-history"}}

    graph.invoke({"recommendation": {"product_name": "Laptop X"}, "human_feedback": ["prefer AMD GPU"]}, config)
    result = graph.invoke(Command(resume={"approved": False, "feedback": "  cheaper  "}), config)
    assert result["human_feedback"] == ["prefer AMD GPU", "cheaper"]

    graph.invoke({"recommendation": {"product_name": "Laptop Y"}, "human_feedback": ["prefer AMD GPU"]}, config)
    result = graph.invoke(Command(resume={"approved": False, "feedback": "   "}), config)
    assert result["human_feedback"] == ["prefer AMD GPU"]
