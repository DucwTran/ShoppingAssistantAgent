def disclose_budget_overrun(recommendation: dict, budget: float | None) -> dict:
    """Make sure a recommendation priced above budget says so, even if the model left it out."""
    price = recommendation.get("price")
    if not budget or price is None or price <= budget:
        return recommendation

    currency = recommendation.get("currency") or "VND"
    note = f"Price {price:,.0f} {currency} exceeds the budget of {budget:,.0f} VND."
    tradeoffs = recommendation.get("tradeoffs") or []
    if not any("budget" in t.lower() or "ngân sách" in t.lower() for t in tradeoffs):
        recommendation = {**recommendation, "tradeoffs": [note, *tradeoffs]}
    return recommendation
