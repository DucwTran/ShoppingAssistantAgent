from typing import TypedDict

import pytest
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.core.metrics import measured


class _State(TypedDict, total=False):
    answer: str


def _reply(tokens_in: int) -> AIMessage:
    return AIMessage(content="ok", response_metadata={"model_name": "fake"},
                     usage_metadata={"input_tokens": tokens_in, "output_tokens": 2, "total_tokens": tokens_in + 2})


def _measured_events(node) -> list[dict]:
    graph = StateGraph(_State)
    graph.add_node("work", measured("work", node))
    graph.add_edge(START, "work")
    graph.add_edge("work", END)
    compiled = graph.compile()
    events = []
    try:
        events.extend(compiled.stream({}, stream_mode="custom"))
    except RuntimeError:
        pass
    return [e for e in events if e["event"] == "node_measured"]


def test_measured_reports_duration_and_tokens_of_every_model_call_in_the_node():
    model = GenericFakeChatModel(messages=iter([_reply(10), _reply(30)]))

    def node(state):
        model.invoke("first")
        model.invoke("second")
        return {"answer": "done"}

    [event] = _measured_events(node)
    assert event["node"] == "work"
    assert event["input_tokens"] == 40 and event["output_tokens"] == 4
    assert event["duration_ms"] >= 0 and event["failed"] is False


def test_measured_reports_a_failed_attempt_with_the_tokens_it_spent():
    model = GenericFakeChatModel(messages=iter([_reply(10)]))

    def node(state):
        model.invoke("spent")
        raise RuntimeError("provider down")

    [event] = _measured_events(node)
    assert event["failed"] is True and event["status"] == "warning"
    assert event["input_tokens"] == 10


def test_measured_keeps_the_node_result_and_error():
    def failing(state):
        raise ValueError("bad")

    assert measured("work", lambda state: {"answer": "x"})({}) == {"answer": "x"}
    with pytest.raises(ValueError):
        measured("work", failing)({})
