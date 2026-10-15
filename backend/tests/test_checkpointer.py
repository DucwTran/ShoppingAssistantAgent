import asyncio
import time
from datetime import datetime, timedelta, timezone

import pytest
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app import main
from app.core.checkpointer import open_checkpointer, prune_checkpoints
from app.graph.nodes.human_approval import human_approval_node
from app.graph.state import ShoppingState


def _approval_graph(checkpointer):
    graph = StateGraph(ShoppingState)
    graph.add_node("human_approval", human_approval_node)
    graph.add_edge(START, "human_approval")
    graph.add_edge("human_approval", END)
    return graph.compile(checkpointer=checkpointer)


def test_paused_thread_survives_reopening_the_database(tmp_path):
    db = tmp_path / "checkpoints.sqlite"
    config = {"configurable": {"thread_id": "restart-test"}}

    with open_checkpointer(db) as saver:
        result = _approval_graph(saver).invoke({"recommendation": {"product_name": "Laptop X"}}, config)
        assert "__interrupt__" in result

    # A fresh connection stands in for a server restart
    with open_checkpointer(db) as saver:
        graph = _approval_graph(saver)
        assert graph.get_state(config).next == ("human_approval",)
        result = graph.invoke(Command(resume={"approved": True, "feedback": None}), config)
        assert result["human_approval"] is True


def test_prune_deletes_only_idle_threads(tmp_path):
    with open_checkpointer(tmp_path / "checkpoints.sqlite") as saver:
        graph = _approval_graph(saver)
        for thread_id in ("a", "b"):
            graph.invoke({"recommendation": {}}, {"configurable": {"thread_id": thread_id}})

        assert prune_checkpoints(saver, timedelta(hours=24)) == 0
        assert graph.get_state({"configurable": {"thread_id": "a"}}).values

        a_day_later = datetime.now(timezone.utc) + timedelta(hours=25)
        assert prune_checkpoints(saver, timedelta(hours=24), now=a_day_later) == 2
        assert not graph.get_state({"configurable": {"thread_id": "a"}}).values

        # The database stays usable after pruning
        result = graph.invoke({"recommendation": {}}, {"configurable": {"thread_id": "c"}})
        assert "__interrupt__" in result


def test_prune_on_empty_database(tmp_path):
    with open_checkpointer(tmp_path / "checkpoints.sqlite") as saver:
        assert prune_checkpoints(saver, timedelta(hours=24)) == 0


def test_shutdown_waits_for_a_running_prune(monkeypatch):
    # The connection is closed right after shutdown; closing it under a running prune crashes the process.
    finished = []

    def slow_prune(saver):
        time.sleep(0.2)
        finished.append(True)

    monkeypatch.setattr(main, "_PRUNE_INTERVAL_SECONDS", 0)
    monkeypatch.setattr(main, "_prune", slow_prune)

    async def shut_down_mid_prune():
        task = asyncio.create_task(main._prune_periodically(saver=None))
        await asyncio.sleep(0.05)  # the prune is now running in its worker thread
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return list(finished)

    assert asyncio.run(shut_down_mid_prune()) == [True]
