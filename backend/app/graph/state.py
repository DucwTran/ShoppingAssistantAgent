from typing import Literal, TypedDict

ResearchStatus = Literal["ok", "empty"]


class ShoppingState(TypedDict, total=False):
    # User input
    query: str

    # Request metadata
    language: str

    # Query understanding / routing
    intent: str  # "shopping" or "general", set by understand_node
    general_reply: str | None

    # Extracted requirements (budget always in VND)
    budget: float | None
    purpose: list[str]
    preferences: dict
    constraints: list[str]

    # Research - raw tool results, collected from tool artifacts (never restated by the model)
    research_hint: str | None  # set by feedback_router when a rejection needs a new search
    web_results: list[dict]
    retrieved_docs: list[dict]
    research_status: ResearchStatus

    # Product processing - each product grounded to a web_results url
    products: list[dict]

    # Evaluation
    quality_score: float
    evaluation_feedback: str

    # Human-in-the-loop
    human_approval: bool | None
    human_feedback: str | None
    human_rejection_count: int

    # Final result
    recommendation: dict


def requirements_of(state: ShoppingState) -> dict:
    return {
        "budget_vnd": state.get("budget"),
        "purpose": state.get("purpose", []),
        "preferences": state.get("preferences", {}),
        "constraints": state.get("constraints", []),
    }
