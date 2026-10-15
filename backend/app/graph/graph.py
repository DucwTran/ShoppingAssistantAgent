from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.core.config import settings
from app.graph.nodes.evaluator import evaluator_node
from app.graph.nodes.extract_products import extract_products_node
from app.graph.nodes.feedback_router import feedback_router_node
from app.graph.nodes.human_approval import human_approval_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.metadata import metadata_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.research_agent import research_agent_node
from app.graph.nodes.understand import understand_node
from app.graph.state import ShoppingState

# For nodes that call the LLM: transient provider/network failures (e.g. Gemini's 503 "high demand")
# are retried after ~3s, then ~6s. research_agent is excluded - it degrades to a direct search instead.
_LLM_RETRY = RetryPolicy(max_attempts=3, initial_interval=3.0)


def _route_after_understand(state: ShoppingState) -> str:
    return "research_agent" if state.get("intent") == "shopping" else END


def _route_after_human_approval(state: ShoppingState) -> str:
    if state.get("human_approval"):
        return END
    if state.get("human_rejection_count", 0) >= settings.max_human_rejections:
        return END
    return "feedback_router"


def _route_after_feedback(state: ShoppingState) -> str:
    return "research_agent" if state.get("research_hint") else "recommend"


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    graph = StateGraph(ShoppingState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("metadata", metadata_node)
    graph.add_node("understand", understand_node, retry_policy=_LLM_RETRY)
    graph.add_node("research_agent", research_agent_node)
    graph.add_node("extract_products", extract_products_node, retry_policy=_LLM_RETRY)
    graph.add_node("recommend", recommend_node, retry_policy=_LLM_RETRY)
    graph.add_node("evaluator", evaluator_node, retry_policy=_LLM_RETRY)
    graph.add_node("human_approval", human_approval_node)
    graph.add_node("feedback_router", feedback_router_node, retry_policy=_LLM_RETRY)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "metadata")
    graph.add_edge("metadata", "understand")
    graph.add_conditional_edges("understand", _route_after_understand, ["research_agent", END])
    graph.add_edge("research_agent", "extract_products")
    graph.add_edge("extract_products", "recommend")
    graph.add_edge("recommend", "evaluator")
    graph.add_edge("evaluator", "human_approval")
    graph.add_conditional_edges("human_approval", _route_after_human_approval, ["feedback_router", END])
    graph.add_conditional_edges("feedback_router", _route_after_feedback, ["research_agent", "recommend"])

    return graph.compile(checkpointer=checkpointer or InMemorySaver())
