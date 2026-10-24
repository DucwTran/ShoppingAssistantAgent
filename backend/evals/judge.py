"""LLM-as-judge for the one quality criterion code cannot check: does the answer serve the stated purpose.

Used offline only - by run_eval on every researched case and by check_judge against hand labels.
At runtime the person approving the recommendation is the judge.
"""

import json

from pydantic import BaseModel, Field

from app.core.structured import invoke_structured
from app.graph.state import question_of, requirements_of

JUDGE_SYSTEM_PROMPT = """You judge one aspect of a laptop-shopping recommendation: how well it serves the user's
stated purpose.

You receive: the user's question, structured requirements, the recommended product (with specs), and knowledge
snippets used. Budget, data grounding and spec completeness are enforced elsewhere - do not score them.

purpose_fit (0-1): does the recommended product (or, when product_name is "N/A", the answer given) actually serve the
stated purpose (e.g. a GPU adequate for AI/gaming, light weight for a student)? Judge from the given specs and
knowledge only.

feedback: name the single most important concrete gap (e.g. "RTX 3050 4GB VRAM is tight for local LLM work"), or
state briefly why it is solid. Never invent a gap that is not present in the data.
"""


class PurposeJudgement(BaseModel):
    purpose_fit: float = Field(ge=0.0, le=1.0, description="How well the recommendation serves the user's stated purpose")
    feedback: str = Field(description="The single most important concrete gap, or briefly why it is solid")


def _recommended_product(state: dict) -> dict | None:
    # One listing page can yield several products, so the url alone is ambiguous; (url, name) is unique
    # because grounding drops duplicate names.
    recommendation = state.get("recommendation") or {}
    url, name = recommendation.get("url"), recommendation.get("product_name")
    return next(
        (p for p in state.get("products", []) if url and p.get("source_url") == url and p.get("name") == name),
        None,
    )


def judge_purpose(state: dict) -> PurposeJudgement:
    payload = {
        "question": question_of(state),
        "requirements": requirements_of(state),
        "recommendation": state.get("recommendation"),
        "recommended_product_specs": _recommended_product(state),
        "knowledge": state.get("retrieved_docs", []),
    }
    return invoke_structured(
        PurposeJudgement,
        [("system", JUDGE_SYSTEM_PROMPT), ("human", json.dumps(payload, ensure_ascii=False))],
    )
