import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState, requirements_of
from app.prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT
from app.schemas.evaluation import PurposeJudgement
from app.schemas.recommendation import NO_PRODUCT

_SPEC_FIELDS = ("cpu", "gpu", "ram", "storage")
_WEIGHTS = {"purpose_fit": 0.35, "grounded": 0.25, "budget_fit": 0.2, "spec_completeness": 0.2}


def _recommended_product(state: ShoppingState) -> dict | None:
    url = (state.get("recommendation") or {}).get("url")
    return next((p for p in state.get("products", []) if url and p.get("source_url") == url), None)


def deterministic_checks(state: ShoppingState) -> tuple[dict[str, float], list[str]]:
    """Score what code can verify exactly; returns (scores, reasons for any shortfall)."""
    recommendation = state.get("recommendation") or {}
    budget = state.get("budget")
    reasons: list[str] = []

    if recommendation.get("product_name") == NO_PRODUCT:
        # A knowledge answer has no price/specs to check; it is only as good as its knowledge support.
        grounded = 1.0 if state.get("retrieved_docs") else 0.3
        if grounded < 1.0:
            reasons.append("no matching products or knowledge were found")
        return {"grounded": grounded, "budget_fit": 1.0, "spec_completeness": 1.0}, reasons

    product = _recommended_product(state)
    grounded = 1.0 if product else 0.0
    if not product:
        reasons.append("recommended product is not among the researched candidates")

    price = recommendation.get("price")
    if not budget:
        budget_fit = 1.0
    elif price is None:
        budget_fit = 0.5
        reasons.append("price unknown, budget fit unverified")
    else:
        budget_fit = 1.0 if price <= budget else 0.0
        if budget_fit == 0.0:
            reasons.append(f"price {price:,.0f} exceeds budget {budget:,.0f}")

    known = [field for field in _SPEC_FIELDS if product and product.get(field, "unknown") != "unknown"]
    spec_completeness = (len(known) + (price is not None)) / (len(_SPEC_FIELDS) + 1)
    missing = [field for field in _SPEC_FIELDS if field not in known]
    if missing:
        reasons.append(f"missing specs: {', '.join(missing)}")

    return {"grounded": grounded, "budget_fit": budget_fit, "spec_completeness": spec_completeness}, reasons


def evaluator_node(state: ShoppingState) -> dict:
    scores, reasons = deterministic_checks(state)

    payload = {
        "question": state["query"],
        "requirements": requirements_of(state),
        "recommendation": state.get("recommendation"),
        "recommended_product_specs": _recommended_product(state),
        "knowledge": state.get("retrieved_docs", []),
    }
    judgement = invoke_structured(
        PurposeJudgement,
        [("system", EVALUATOR_SYSTEM_PROMPT), ("human", json.dumps(payload, ensure_ascii=False))],
    )
    scores["purpose_fit"] = judgement.purpose_fit

    score = round(sum(_WEIGHTS[name] * value for name, value in scores.items()), 2)
    feedback = " ".join([judgement.feedback, *(f"[{reason}]" for reason in reasons)])

    emit("evaluator_done", "Recommendation quality evaluated", node="evaluator", score=score, **scores)
    return {"quality_score": score, "evaluation_feedback": feedback}
