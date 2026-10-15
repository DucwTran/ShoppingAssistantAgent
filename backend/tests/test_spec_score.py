from app.tools.spec_score import score_product_spec

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
    result = score_product_spec(_FULL_SPEC_PRODUCT, budget=25_000_000)
    assert result["score"] == 1.0
    assert result["reasons"] == []


def test_score_product_spec_penalizes_over_budget():
    result = score_product_spec(_FULL_SPEC_PRODUCT, budget=10_000_000)
    assert result["score"] < 1.0
    assert any("budget" in reason for reason in result["reasons"])


def test_score_product_spec_penalizes_unknown_fields():
    partial_product = {**_FULL_SPEC_PRODUCT, "cpu": "unknown", "gpu": "unknown"}
    result = score_product_spec(partial_product, budget=25_000_000)
    assert result["score"] < 1.0
    assert any("missing spec info" in reason for reason in result["reasons"])


def test_score_product_spec_treats_missing_fields_as_unknown():
    result = score_product_spec({"name": "A", "price": 20_000_000}, budget=25_000_000)
    assert result["score"] == 0.6


def test_score_product_spec_no_budget_skips_budget_check():
    result = score_product_spec(_FULL_SPEC_PRODUCT)
    assert result["score"] == 1.0
