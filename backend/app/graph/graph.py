from langgraph.graph import END, START, StateGraph

from app.graph.nodes.analyzer import analyzer_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.metadata import metadata_node
from app.graph.nodes.normalize import normalize_node
from app.graph.nodes.rag import rag_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.router import router_node
from app.graph.nodes.web_search import web_search_node
from app.graph.state import ShoppingState


def _route_after_router(state: ShoppingState) -> list[str]:
    branches = []
    if state.get("use_web"):
        branches.append("web_search")
    if state.get("use_rag"):
        branches.append("rag")
    return branches or ["web_search"]


def build_graph():
    graph = StateGraph(ShoppingState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("metadata", metadata_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("router", router_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("rag", rag_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("recommend", recommend_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "metadata")
    graph.add_edge("metadata", "analyzer")
    graph.add_edge("analyzer", "router")
    graph.add_conditional_edges("router", _route_after_router, ["web_search", "rag"])
    graph.add_edge("web_search", "normalize")
    graph.add_edge("normalize", "recommend")
    graph.add_edge("rag", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile()
