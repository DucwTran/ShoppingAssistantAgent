from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.core.config import settings
from app.core.metrics import measured
from app.graph.nodes.extract_products import extract_products_node
from app.graph.nodes.feedback_router import feedback_router_node
from app.graph.nodes.human_approval import human_approval_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.record_turn import record_turn_node
from app.graph.nodes.research_agent import research_agent_node
from app.graph.nodes.understand import understand_node
from app.graph.state import ShoppingState

# For nodes that call the LLM: transient provider/network failures (e.g. Gemini's 503 "high demand")
# are retried after ~3s, then ~6s. research_agent is excluded - it degrades to a direct search instead.
_LLM_RETRY = RetryPolicy(max_attempts=3, initial_interval=3.0)


def _route_after_understand(state: ShoppingState) -> str:
    return "research_agent" if state.get("intent") == "shopping" else "record_turn"


def _route_after_human_approval(state: ShoppingState) -> str:
    if state.get("human_approval"):
        return "record_turn"
    if state.get("human_rejection_count", 0) >= settings.max_human_rejections:
        return "record_turn"
    return "feedback_router"


def _route_after_feedback(state: ShoppingState) -> str:
    return "research_agent" if state.get("research_hint") else "recommend"


def _add_llm_node(graph: StateGraph, name: str, node, retry_policy: RetryPolicy | None = _LLM_RETRY) -> None:
    """Nodes that call the LLM report their duration and token usage (see app.core.metrics)."""
    graph.add_node(name, measured(name, node), retry_policy=retry_policy)


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(ShoppingState)
    graph.add_node("input_validation", input_validation_node)
    _add_llm_node(graph, "understand", understand_node)
    _add_llm_node(graph, "research_agent", research_agent_node, retry_policy=None)
    _add_llm_node(graph, "extract_products", extract_products_node)
    _add_llm_node(graph, "recommend", recommend_node)
    graph.add_node("human_approval", human_approval_node)
    _add_llm_node(graph, "feedback_router", feedback_router_node)
    graph.add_node("record_turn", record_turn_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "understand")
    graph.add_conditional_edges("understand", _route_after_understand, ["research_agent", "record_turn"])
    graph.add_edge("research_agent", "extract_products")
    graph.add_edge("extract_products", "recommend")
    graph.add_edge("recommend", "human_approval")
    graph.add_conditional_edges("human_approval", _route_after_human_approval, ["feedback_router", "record_turn"])
    graph.add_conditional_edges("feedback_router", _route_after_feedback, ["research_agent", "recommend"])
    graph.add_edge("record_turn", END)

    return graph.compile(checkpointer=checkpointer or InMemorySaver())
