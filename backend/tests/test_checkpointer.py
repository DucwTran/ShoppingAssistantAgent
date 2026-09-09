from langgraph.checkpoint.memory import InMemorySaver

from app.core.checkpointer import get_checkpointer


def test_get_checkpointer_returns_in_memory_saver():
    assert isinstance(get_checkpointer(), InMemorySaver)


def test_get_checkpointer_returns_distinct_instances():
    assert get_checkpointer() is not get_checkpointer()
