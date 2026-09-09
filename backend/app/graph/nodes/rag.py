from app.core.events import emit
from app.graph.state import ShoppingState
from app.rag.retriever import retrieve


def rag_node(state: ShoppingState) -> dict:
    docs = retrieve(state["query"], k=4)

    emit("rag_done", "Knowledge retrieved", node="rag", count=len(docs))

    return {"retrieved_docs": docs}
