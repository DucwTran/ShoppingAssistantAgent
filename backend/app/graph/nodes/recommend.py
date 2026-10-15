import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.nodes.metadata import language_name
from app.graph.state import ShoppingState, requirements_of
from app.guards.recommendation_guard import disclose_budget_overrun
from app.prompts.recommend_prompt import RECOMMEND_SYSTEM_PROMPT
from app.schemas.recommendation import NO_PRODUCT, Recommendation, RecommendationChoice
from app.tools.compare import price_extremes
from app.tools.spec_score import score_product_spec


def rank_candidates(products: list[dict], budget: float | None) -> list[dict]:
    """Give each product a stable id and its deterministic spec score, best first."""
    candidates = []
    for product_id, product in enumerate(products):
        spec = score_product_spec(product, budget)
        candidates.append({"id": product_id, **product, "spec_score": spec["score"], "score_reasons": spec["reasons"]})
    return sorted(candidates, key=lambda c: c["spec_score"], reverse=True)


def _check_choice(valid_ids: set[int]):
    def check(choice: RecommendationChoice) -> None:
        for field in ("product_id", "alternative_id"):
            value = getattr(choice, field)
            if value is not None and value not in valid_ids:
                raise ValueError(f"{field}={value} is not a candidate id")

    return check


def build_recommendation(choice: RecommendationChoice, candidates: list[dict]) -> dict:
    """Product facts come from the candidate the model picked, never from model-written text."""
    by_id = {c["id"]: c for c in candidates}
    chosen = by_id.get(choice.product_id)
    alternative = by_id.get(choice.alternative_id) if choice.alternative_id != choice.product_id else None
    return Recommendation(
        product_name=chosen["name"] if chosen else NO_PRODUCT,
        price=chosen["price"] if chosen else None,
        currency=chosen["currency"] if chosen else None,
        url=chosen["source_url"] if chosen else None,
        why_it_fits=choice.why_it_fits,
        tradeoffs=choice.tradeoffs,
        alternative=alternative["name"] if alternative else None,
        confidence=choice.confidence,
    ).model_dump()


def recommend_node(state: ShoppingState) -> dict:
    budget = state.get("budget")
    products = state.get("products", [])
    candidates = rank_candidates(products, budget)

    payload = {
        "question": state["query"],
        "requirements": requirements_of(state),
        "candidates": candidates,
        "price_extremes": price_extremes(products),
        "knowledge": state.get("retrieved_docs", []),
        "research_status": state.get("research_status", "ok"),
        "human_feedback": state.get("human_feedback"),
    }
    choice = invoke_structured(
        RecommendationChoice,
        [
            ("system", RECOMMEND_SYSTEM_PROMPT.format(language=language_name(state.get("language")))),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
        check=_check_choice({c["id"] for c in candidates}),
    )
    recommendation = disclose_budget_overrun(build_recommendation(choice, candidates), budget)

    emit(
        "recommend_done",
        "Recommendation generated",
        node="recommend",
        product=recommendation["product_name"],
        confidence=recommendation["confidence"],
    )
    return {"recommendation": recommendation}
