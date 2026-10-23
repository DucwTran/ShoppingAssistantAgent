from app.tools import price_lookup
from app.tools.price_lookup import fill_missing_prices, model_codes, price_near_code


def test_model_codes_keep_only_sku_like_tokens():
    assert model_codes("Acer Nitro V 15 ANV15-41-R1JY") == ["anv15-41-r1jy"]
    assert model_codes("HP 15-FD0083TU") == ["15-fd0083tu"]
    assert model_codes("ASUS Vivobook 14 X1404VA-NK394W") == ["x1404va-nk394w"]
    assert model_codes("Acer Nitro V 15") == []  # no code: cannot be matched to one listing


def test_price_near_code_reads_the_price_of_that_model_only():
    text = ("Laptop MSI Cyborg 15 A13UC-2088VN i5 16GB 19.400.000đ\n"
            "Laptop Acer Nitro V 15 ANV15-41-R1JY Ryzen 5 RTX 3050 19.900.000₫ 24.990.000₫")
    assert price_near_code("anv15-41-r1jy", text) == 19_900_000
    assert price_near_code("a13uc-2088vn", text) == 19_400_000
    assert price_near_code("x1404va", text) is None


def test_price_near_code_ignores_a_price_far_from_the_code():
    assert price_near_code("anv15-41-r1jy", "ANV15-41-R1JY" + " " * 400 + "19.900.000đ") is None


def test_fill_missing_prices_searches_only_for_priceless_coded_products(monkeypatch):
    queries = []

    def search(query, max_results):
        queries.append(query)
        return [{"url": "https://fptshop.com.vn/acer-anv15", "title": "Acer Nitro V ANV15-41-R1JY",
                 "content": "", "price_listing": "Acer Nitro V ANV15-41-R1JY 19.990.000đ"}]

    monkeypatch.setattr(price_lookup, "search_web", search)
    products = [
        {"name": "Acer Nitro V 15 ANV15-41-R1JY", "price": None, "currency": "VND"},
        {"name": "ASUS TUF A15", "price": None, "currency": "VND"},  # no model code: not looked up
        {"name": "MSI Cyborg 15 A13UC", "price": 19_400_000, "currency": "VND"},  # already priced
    ]

    assert fill_missing_prices(products) == 1
    assert queries == ["Acer Nitro V 15 ANV15-41-R1JY"]
    assert products[0]["price"] == 19_990_000
    assert products[0]["price_source_url"] == "https://fptshop.com.vn/acer-anv15"
    assert products[1]["price"] is None


def test_fill_missing_prices_survives_a_failed_search(monkeypatch):
    def failing(query, max_results):
        raise TimeoutError("tavily")

    monkeypatch.setattr(price_lookup, "search_web", failing)
    products = [{"name": "HP 15-FD0083TU", "price": None, "currency": "VND"}]
    assert fill_missing_prices(products) == 0
    assert products[0]["price"] is None
