from typing import TypedDict


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

    # Retrieval
    retrieved_docs: list

    # Product processing
    products: list

    # Evaluation
    quality_score: float
    evaluation_feedback: str

    # Human-in-the-loop
    human_approval: bool | None
    human_feedback: str | None
    human_rejection_count: int

    # Final result
    recommendation: dict
    general_reply: str | None
