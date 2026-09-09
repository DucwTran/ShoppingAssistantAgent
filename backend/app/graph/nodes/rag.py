from app.core.events import emit
from app.graph.state import ShoppingState
from app.rag.retriever import retrieve


def rag_node(state: ShoppingState) -> dict:
    is_reflecting = state.get("reflection_count", 0) > 0 and state.get("search_query")
    query = state["search_query"] if is_reflecting else state["query"]
    docs = retrieve(query, k=4)

    emit("rag_done", "Knowledge retrieved", node="rag", count=len(docs))

    return {"retrieved_docs": docs}
