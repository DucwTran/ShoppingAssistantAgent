import pytest

from app.core.config import settings
from app.graph.nodes.router import router_node

REQUIRES_LIVE_KEY = not settings.google_api_key
SKIP_REASON = "Requires real GOOGLE_API_KEY in .env"


@pytest.mark.skipif(REQUIRES_LIVE_KEY, reason=SKIP_REASON)
def test_router_web_only_for_product_discovery():
    result = router_node({"query": "Tim laptop gaming duoi 25 trieu"})
    assert result["use_web"] is True


@pytest.mark.skipif(REQUIRES_LIVE_KEY, reason=SKIP_REASON)
def test_router_rag_only_for_technical_question():
    result = router_node({"query": "RTX 4060 co du cho AI development khong?"})
    assert result["use_rag"] is True


@pytest.mark.skipif(REQUIRES_LIVE_KEY, reason=SKIP_REASON)
def test_router_both_for_combined_question():
    result = router_node({"query": "Laptop nao duoi 25 trieu tot nhat cho AI development va gaming?"})
    assert result["use_web"] is True
    assert result["use_rag"] is True
