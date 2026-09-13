from langgraph.graph import END, START, StateGraph

from app.core.checkpointer import get_checkpointer
from app.core.config import settings
from app.core.events import emit
from app.graph.nodes.analyzer import analyzer_node
from app.graph.nodes.comparison import comparison_node
from app.graph.nodes.evaluator import evaluator_node
from app.graph.nodes.human_approval import human_approval_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.intent import intent_node
from app.graph.nodes.metadata import metadata_node
from app.graph.nodes.normalize import normalize_node
from app.graph.nodes.rag import rag_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.reflection import reflection_node
from app.graph.nodes.router import router_node
from app.graph.nodes.web_search import web_search_node
from app.graph.state import ShoppingState


def _route_by_source_flags(state: ShoppingState) -> list[str]:
    branches = []
    if state.get("use_web"):
        branches.append("web_search")
    if state.get("use_rag"):
        branches.append("rag")
    return branches or ["web_search"]


def _route_after_evaluator(state: ShoppingState) -> str:
    quality_score = state.get("quality_score", 0.0)
    reflection_count = state.get("reflection_count", 0)

    if quality_score >= settings.quality_threshold:
        branch = "proceed"
        next_node = "human_approval"
    elif reflection_count >= settings.max_reflections:
        branch = "degrade"
        next_node = "human_approval"
    else:
        branch = "reflect"
        next_node = "reflection"

    emit(
        "evaluator_routed",
        f"Evaluator routing decision: {branch}",
        node="evaluator",
        branch=branch,
        quality_score=quality_score,
        reflection_count=reflection_count,
    )
    return next_node


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
    graph.add_node("router", router_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("rag", rag_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("recommend", recommend_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("human_approval", human_approval_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "intent")
    graph.add_conditional_edges("intent", _route_after_intent, ["metadata", END])
    graph.add_edge("metadata", "analyzer")
    graph.add_edge("analyzer", "router")
    graph.add_conditional_edges("router", _route_by_source_flags, ["web_search", "rag"])
    graph.add_edge("web_search", "normalize")
    graph.add_edge("rag", "normalize")
    graph.add_edge("normalize", "comparison")
    graph.add_edge("comparison", "recommend")
    graph.add_edge("recommend", "evaluator")
    graph.add_conditional_edges("evaluator", _route_after_evaluator, ["reflection", "human_approval"])
    graph.add_conditional_edges("reflection", _route_by_source_flags, ["web_search", "rag"])
    graph.add_conditional_edges("human_approval", _route_after_human_approval, ["recommend", END])

    return graph.compile(checkpointer=get_checkpointer())
