from app.schemas.spec_score import ScoreProductSpecArgs
from app.tools.base import RegisteredTool

_SPEC_FIELDS = ("cpu", "gpu", "ram", "storage")


def _score_product_spec(product: dict, budget: float | None = None) -> dict:
    score = 1.0
    reasons = []

    price = product.get("price")
    if budget and isinstance(price, (int, float)) and price > budget:
        score -= 0.4
        reasons.append(f"price {price} exceeds budget {budget}")

    unknown_fields = [field for field in _SPEC_FIELDS if product.get(field) == "unknown"]
    if unknown_fields:
        score -= 0.1 * len(unknown_fields)
        reasons.append(f"missing spec info: {', '.join(unknown_fields)}")

    return {"score": round(max(0.0, min(1.0, score)), 2), "reasons": reasons}


score_product_spec_tool = RegisteredTool(
    name="score_product_spec",
    description="Score how well one product fits the budget and how complete its spec data is (0-1, higher is better).",
    args_schema=ScoreProductSpecArgs,
    func=_score_product_spec,
)
