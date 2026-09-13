from app.rag.embeddings import get_embeddings
from app.rag.retriever import retrieve


def test_embeddings_return_vector():
    vector = get_embeddings().embed_query("laptop for AI development")
    assert len(vector) > 0


def test_retriever_finds_relevant_chunk():
    results = retrieve("RTX 4060 co du cho AI development khong?", k=3)
    assert len(results) > 0
    assert any("gpu" in r["source"].lower() for r in results)
