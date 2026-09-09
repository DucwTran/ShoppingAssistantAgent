from typing import Any, TypedDict


class ShoppingState(TypedDict, total=False):
    # User input
    query: str

    # Request metadata (Phase 1)
    language: str
    detected_at: str

    # Extracted requirements (Phase 1)
    budget: float | None
    purpose: list[str]
    preferences: dict
    constraints: list[str]

    # Query analysis (Phase 2 router)
    intent: str
    use_web: bool
    use_rag: bool

    # Retrieval
    search_query: str
    search_results: list
    retrieved_docs: list

    # Product processing (Phase 1)
    products: list
    comparison: list

    # Evaluation (Phase 3)
    quality_score: float
    evaluation_feedback: str

    # Reflection (Phase 3)
    reflection_count: int
    reflection_reason: str

    # HITL (Phase 4)
    human_approval: bool | None
    human_feedback: str | None

    # Final result (Phase 1)
    recommendation: dict

    # Session (Phase 1 CLI / Phase 4-5 API)
    thread_id: str
    log: list[dict[str, Any]]
