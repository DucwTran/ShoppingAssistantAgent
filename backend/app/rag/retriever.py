from app.rag.vectorstore import get_vectorstore


def retrieve(query: str, k: int = 4) -> list[dict]:
    store = get_vectorstore()
    results = store.similarity_search(query, k=k)
    return [{"text": doc.page_content, "source": doc.metadata.get("source", "unknown")} for doc in results]
