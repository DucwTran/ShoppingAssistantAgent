from typing import Any, TypedDict


class ShoppingState(TypedDict, total=False):
    # User input
    query: str

    # Request metadata
    language: str
    detected_at: str

    # Extracted requirements
    budget: float | None
    purpose: list[str]
    preferences: dict
    constraints: list[str]

    # Query analysis / routing
    intent: str  # "shopping" or "general", set by intent_node
    use_web: bool
    use_rag: bool

    # Retrieval
    search_query: str
    search_results: list
    retrieved_docs: list

    # Product processing
    products: list
    comparison: list

    # Evaluation
    quality_score: float
    evaluation_feedback: str

    # Reflection
    reflection_count: int
    reflection_reason: str

    # Human-in-the-loop
    human_approval: bool | None
    human_feedback: str | None

    # Final result
    recommendation: dict
    general_reply: str | None

    # Session
    log: list[dict[str, Any]]
