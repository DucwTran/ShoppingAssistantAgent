from app.tools.registry import TOOLS_BY_NAME

_FULL_SPEC_PRODUCT = {
    "name": "A",
    "price": 20_000_000,
    "currency": "VND",
    "cpu": "Ryzen 7",
    "gpu": "RTX 4060",
    "ram": "16GB",
    "storage": "512GB SSD",
}


def test_score_product_spec_full_score_within_budget():
    result = TOOLS_BY_NAME["score_product_spec"].run(product=_FULL_SPEC_PRODUCT, budget=25_000_000)
    assert result["score"] == 1.0
    assert result["reasons"] == []


def test_score_product_spec_penalizes_over_budget():
    result = TOOLS_BY_NAME["score_product_spec"].run(product=_FULL_SPEC_PRODUCT, budget=10_000_000)
    assert result["score"] < 1.0
    assert any("budget" in reason for reason in result["reasons"])


def test_score_product_spec_penalizes_unknown_fields():
    partial_product = {**_FULL_SPEC_PRODUCT, "cpu": "unknown", "gpu": "unknown"}
    result = TOOLS_BY_NAME["score_product_spec"].run(product=partial_product, budget=25_000_000)
    assert result["score"] < 1.0
    assert any("missing spec info" in reason for reason in result["reasons"])


def test_score_product_spec_no_budget_skips_budget_check():
    result = TOOLS_BY_NAME["score_product_spec"].run(product=_FULL_SPEC_PRODUCT)
    assert result["score"] == 1.0
