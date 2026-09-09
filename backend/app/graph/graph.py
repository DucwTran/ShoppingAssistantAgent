from langgraph.graph import END, START, StateGraph

from app.graph.nodes.analyzer import analyzer_node
from app.graph.nodes.input_validation import input_validation_node
from app.graph.nodes.metadata import metadata_node
from app.graph.nodes.normalize import normalize_node
from app.graph.nodes.recommend import recommend_node
from app.graph.nodes.web_search import web_search_node
from app.graph.state import ShoppingState


def build_graph():
    graph = StateGraph(ShoppingState)
    graph.add_node("input_validation", input_validation_node)
    graph.add_node("metadata", metadata_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("web_search", web_search_node)
    graph.add_node("normalize", normalize_node)
    graph.add_node("recommend", recommend_node)

    graph.add_edge(START, "input_validation")
    graph.add_edge("input_validation", "metadata")
    graph.add_edge("metadata", "analyzer")
    graph.add_edge("analyzer", "web_search")
    graph.add_edge("web_search", "normalize")
    graph.add_edge("normalize", "recommend")
    graph.add_edge("recommend", END)

    return graph.compile()
