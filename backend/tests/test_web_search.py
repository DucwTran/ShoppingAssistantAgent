from app.graph.nodes.web_search import _build_search_query, _resolve_search_query


def test_build_search_query_includes_purpose_and_budget():
    query = _build_search_query({"purpose": ["AI development", "gaming"], "budget": 25_000_000})
    assert "laptop" in query
    assert "AI development, gaming" in query
    assert "25000000" in query


def test_build_search_query_minimal_state():
    assert _build_search_query({}) == "laptop"


def test_resolve_search_query_builds_fresh_on_first_pass():
    state = {"purpose": ["gaming"], "budget": 20_000_000}
    assert _resolve_search_query(state) == _build_search_query(state)


def test_resolve_search_query_uses_reflection_query_when_reflecting():
    state = {
        "reflection_count": 1,
        "search_query": "battery life comparison for top candidates",
        "purpose": ["gaming"],
    }
    assert _resolve_search_query(state) == "battery life comparison for top candidates"


def test_resolve_search_query_ignores_stale_query_when_not_reflecting():
    state = {"reflection_count": 0, "search_query": "leftover from a previous run", "purpose": ["gaming"]}
    assert _resolve_search_query(state) == _build_search_query(state)
