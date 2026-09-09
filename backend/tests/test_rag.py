import pytest

from app.core.config import settings
from app.rag.embeddings import get_embeddings
from app.rag.retriever import retrieve

REQUIRES_LIVE_KEY = not settings.google_api_key
SKIP_REASON = "Requires real GOOGLE_API_KEY in .env"


@pytest.mark.skipif(REQUIRES_LIVE_KEY, reason=SKIP_REASON)
def test_embeddings_return_vector():
    vector = get_embeddings().embed_query("laptop for AI development")
    assert len(vector) > 0


@pytest.mark.skipif(REQUIRES_LIVE_KEY, reason=SKIP_REASON)
def test_retriever_finds_relevant_chunk():
    results = retrieve("RTX 4060 co du cho AI development khong?", k=3)
    assert len(results) > 0
    assert any("gpu" in r["source"].lower() for r in results)
