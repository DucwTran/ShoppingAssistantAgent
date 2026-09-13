from langgraph.graph import END, START, StateGraph

from app.core.checkpointer import get_checkpointer
from app.core.config import settings
from app.core.events import emit
from app.graph.nodes.analyzer import analyzer_node
from app.graph.nodes.evaluator import evaluator_node
from app.graph.nodes.human_approval import human_approval_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.intent import intent_node
from app.graph.nodes.metadata import metadata_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.research_agent import research_agent_node
from app.graph.state import ShoppingState


def _route_after_human_approval(state: ShoppingState) -> str:
    if state.get("human_approval"):
        return END
    if state.get("human_rejection_count", 0) >= settings.max_human_rejections:
        return END
    return "recommend"


def _route_after_intent(state: ShoppingState) -> str:
    return "metadata" if state.get("intent") == "shopping" else END


def build_graph():
    graph = StateGraph(ShoppingState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("intent", intent_node)
    graph.add_node("metadata", metadata_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("research_agent", research_agent_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("human_approval", human_approval_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "intent")
    graph.add_conditional_edges("intent", _route_after_intent, ["metadata", END])
    graph.add_edge("metadata", "analyzer")
    graph.add_edge("analyzer", "research_agent")
    graph.add_edge("research_agent", "recommend")
    graph.add_edge("recommend", "evaluator")
    graph.add_edge("evaluator", "human_approval")
    graph.add_conditional_edges("human_approval", _route_after_human_approval, ["recommend", END])

    return graph.compile(checkpointer=get_checkpointer())
