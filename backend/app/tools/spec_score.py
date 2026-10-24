from app.schemas.product import SPEC_FIELDS


def score_product_spec(product: dict, budget: float | None = None) -> dict:
    """Score budget fit and spec completeness of one product (0-1, higher is better)."""
    score = 1.0
    reasons = []

    price = product.get("price")
    if budget and isinstance(price, (int, float)) and price > budget:
        score -= 0.4
        reasons.append(f"price {price} exceeds budget {budget}")

    unknown_fields = [field for field in SPEC_FIELDS if product.get(field, "unknown") == "unknown"]
    if unknown_fields:
        score -= 0.1 * len(unknown_fields)
        reasons.append(f"missing spec info: {', '.join(unknown_fields)}")

    return {"score": round(max(0.0, min(1.0, score)), 2), "reasons": reasons}
