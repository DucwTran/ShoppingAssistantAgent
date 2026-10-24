import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.graph.nodes.recommend import _check_choice, build_recommendation, rank_candidates
from app.graph.nodes.research_agent import _collect_artifacts, _fallback_query
from app.guards.grounding_guard import ground_products
from app.guards.input_guard import validate_input
from app.guards.recommendation_guard import disclose_budget_overrun
from app.schemas.recommendation import RecommendationChoice

_PRODUCTS = [
    {"name": "A", "price": 30_000_000, "currency": "VND", "cpu": "i7", "gpu": "RTX 4060", "ram": "16GB",
     "storage": "1TB", "source_url": "https://a.vn/a"},
    {"name": "B", "price": 20_000_000, "currency": "VND", "cpu": "i5", "gpu": "RTX 4050", "ram": "16GB",
     "storage": "512GB", "source_url": "https://b.vn/b"},
]


# --- guards ----------------------------------------------------------------------------------------


def test_ground_products_drops_unknown_sources_and_duplicates():
    products = [
        {"name": "A", "source_url": "https://a.vn/a/"},  # trailing slash still matches
        {"name": "a", "source_url": "https://a.vn/a"},  # duplicate name
        {"name": "Ghost", "source_url": "https://nowhere.example"},
        {"name": "NoSource"},
    ]
    kept, dropped, _ = ground_products(products, {"https://a.vn/a": "Laptop A"})
    assert [p["name"] for p in kept] == ["A"]
    assert dropped == 3


def test_ground_products_keeps_facts_stated_by_the_source():
    product = {"name": "Acer Nitro V", "price": 22_990_000, "cpu": "i5-13420H", "gpu": "RTX 4050",
               "ram": "16GB", "storage": "512GB SSD", "source_url": "https://a.vn/a"}
    source = "Acer Nitro V i5-13420H RTX 4050 16 GB SSD 512GB - 22.990.000đ"
    kept, _, cleared = ground_products([dict(product)], {"https://a.vn/a": source})
    assert kept == [product]
    assert cleared == 0


@pytest.mark.parametrize("source", ["Giá 22,99 triệu", "price 22,990,000 VND"])
def test_ground_products_reads_other_price_formats(source):
    kept, _, _ = ground_products([{"name": "A", "price": 22_990_000, "source_url": "u"}], {"u": source})
    assert kept[0]["price"] == 22_990_000


def test_ground_products_clears_facts_missing_from_the_source():
    product = {"name": "Acer Nitro V", "price": 21_990_000, "cpu": "unknown", "gpu": "RTX 4060",
               "ram": "16GB", "storage": "unknown", "source_url": "https://a.vn/a"}
    source = "Acer Nitro V RTX 4050 16GB - 22.990.000đ"
    kept, _, cleared = ground_products([product], {"https://a.vn/a": source})
    assert kept[0]["price"] is None  # 21.990.000 is not on the page
    assert kept[0]["gpu"] == "unknown"  # the page lists an RTX 4050, not a 4060
    assert kept[0]["ram"] == "16GB"
    assert cleared == 2


def test_disclose_budget_overrun_adds_note_once():
    over = {"price": 30_000_000, "currency": "VND", "tradeoffs": []}
    assert "budget" in disclose_budget_overrun(over, 25_000_000)["tradeoffs"][0]

    already = {"price": 30_000_000, "tradeoffs": ["Vượt ngân sách 5 triệu"]}
    assert disclose_budget_overrun(already, 25_000_000)["tradeoffs"] == ["Vượt ngân sách 5 triệu"]

    within = {"price": 20_000_000, "tradeoffs": []}
    assert disclose_budget_overrun(within, 25_000_000)["tradeoffs"] == []


def test_input_guard_normalizes_and_strips_control_chars():
    assert validate_input("laptop\x00 gaming​") == "laptop gaming"
    # decomposed "ữ" (u + horn + tilde) is normalized to the precomposed character
    assert validate_input("dữơi") == "dữơi"


# --- recommend -------------------------------------------------------------------------------------


def test_rank_candidates_puts_within_budget_first():
    ranked = rank_candidates(_PRODUCTS, budget=25_000_000)
    assert [c["name"] for c in ranked] == ["B", "A"]
    assert {c["id"] for c in ranked} == {0, 1}


def test_build_recommendation_takes_facts_from_candidate():
    candidates = rank_candidates(_PRODUCTS, budget=None)
    choice = RecommendationChoice(product_id=1, alternative_id=0, why_it_fits=["x"], confidence=0.7)
    recommendation = build_recommendation(choice, candidates)
    assert recommendation["product_name"] == "B"
    assert recommendation["price"] == 20_000_000
    assert recommendation["url"] == "https://b.vn/b"
    assert recommendation["alternative"] == "A"


def test_build_recommendation_without_choice_is_na():
    choice = RecommendationChoice(product_id=None, why_it_fits=["no match"], confidence=0.2)
    recommendation = build_recommendation(choice, [])
    assert recommendation["product_name"] == "N/A"
    assert recommendation["url"] is None


def test_check_choice_rejects_unknown_ids():
    check = _check_choice({0, 1})
    check(RecommendationChoice(product_id=1, why_it_fits=["x"], confidence=0.5))
    with pytest.raises(ValueError):
        check(RecommendationChoice(product_id=5, why_it_fits=["x"], confidence=0.5))


# --- research --------------------------------------------------------------------------------------


def test_collect_artifacts_reads_tool_messages_only():
    messages = [
        AIMessage(content="", tool_calls=[{"name": "web_search", "args": {}, "id": "1"}]),
        ToolMessage(content="trimmed", artifact=[{"title": "T", "url": "u"}], name="web_search", tool_call_id="1"),
        ToolMessage(content="trimmed", artifact=[{"text": "d", "source": "s"}], name="search_knowledge_base",
                    tool_call_id="2"),
        ToolMessage(content="failed", artifact=[], name="web_search", tool_call_id="3"),
        AIMessage(content="Done."),
    ]
    web_results, docs = _collect_artifacts(messages)
    assert web_results == [{"title": "T", "url": "u"}]
    assert docs == [{"text": "d", "source": "s"}]


def test_fallback_query_uses_hint_and_budget():
    assert _fallback_query({"query": "laptop gaming", "budget": 25_000_000}) == "laptop gaming dưới 25 triệu"
    assert _fallback_query({"query": "q", "research_hint": "laptop AMD"}).startswith("laptop AMD")


def test_fallback_query_does_not_repeat_a_stated_budget():
    query = "laptop dưới 25 triệu cho lập trình AI và gaming"
    assert _fallback_query({"query": query, "budget": 25_000_000}) == query
    # "250" is not the budget "25"
    assert _fallback_query({"query": "laptop 250GB", "budget": 25_000_000}) == "laptop 250GB dưới 25 triệu"


def test_condense_keeps_price_lines_and_drops_raw_page():
    from app.tools.web_search import _condense

    result = _condense({
        "title": "T", "url": "u", "content": "snippet",
        "raw_content": "Header\nLaptop Acer Nitro V 15 i5/16GB 19.290.000đ 22.990.000đ\nFooter\nMSI Cyborg 27,490,000đ",
    })
    assert "raw_content" not in result
    assert result["content"] == "snippet"
    assert "19.290.000đ" in result["price_listing"] and "27,490,000đ" in result["price_listing"]
    assert "Footer" not in result["price_listing"]
    assert "price_listing" not in _condense({"title": "T", "url": "u", "content": "s", "raw_content": "no prices"})


def test_extraction_sees_and_verifies_prices_behind_a_long_snippet(fake_pipeline):
    # Regression: the price lines used to be appended to `content`, past the characters sent to the model
    from app.graph.nodes.extract_products import _CONTENT_CHARS, extract_products_node
    from tests.conftest import WEB_RESULTS

    page = {"title": "Laptop Acer Nitro V 15 RTX 4050", "url": WEB_RESULTS[0]["url"],
            "content": "i5-13420H 16GB SSD 512GB " + "x" * _CONTENT_CHARS,
            "price_listing": "Acer Nitro V 15 i5-13420H 16GB 22.990.000đ"}
    state = {"query": "laptop gaming", "web_results": [page, WEB_RESULTS[1]]}

    products = extract_products_node(state)["products"]

    sent = fake_pipeline.payloads["ProductExtraction"]["search_results"][0]
    assert sent["price_listing"] == page["price_listing"]
    assert products[0]["name"] == "Acer Nitro V 15" and products[0]["price"] == 22_990_000


def test_extraction_prices_missing_products_by_lookup_and_drops_the_rest(fake_pipeline):
    from app.graph.nodes.extract_products import extract_products_node
    from app.schemas.product import Product
    from tests.conftest import WEB_RESULTS

    fake_pipeline.extracted = [
        Product(name="Acer Nitro V 15 ANV15-41", source_url=WEB_RESULTS[0]["url"]),  # priceless, has a model code
        Product(name="Dell Inspiron", source_url=WEB_RESULTS[0]["url"]),  # priceless, nothing to look up
        Product(name="ASUS TUF A15", price=26_490_000, source_url=WEB_RESULTS[1]["url"]),
    ]
    fake_pipeline.price_lookup_results = [{"url": "https://fptshop.com.vn/anv15-41", "title": "Acer Nitro V ANV15-41",
                                           "content": "Acer Nitro V ANV15-41 Ryzen 5 RTX 3050 21.990.000đ"}]

    products = extract_products_node({"query": "laptop gaming", "web_results": WEB_RESULTS})["products"]

    assert [p["name"] for p in products] == ["Acer Nitro V 15 ANV15-41", "ASUS TUF A15"]
    assert products[0]["price"] == 21_990_000
    assert products[0]["price_source_url"] == "https://fptshop.com.vn/anv15-41"
    assert fake_pipeline.thinking_levels["ProductExtraction"] == "low"


def test_select_results_prefers_pages_with_prices_and_caps_the_count():
    from app.graph.nodes.extract_products import _MAX_RESULTS, select_results

    results = [{"url": f"u{i}", "price_listing": "19.990.000đ" if i % 5 == 4 else None} for i in range(20)]
    selected = select_results(results)
    assert len(selected) == _MAX_RESULTS
    assert [r["url"] for r in selected[:4]] == ["u4", "u9", "u14", "u19"]
    assert selected[4]["url"] == "u0"
