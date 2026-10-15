from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.nodes.metadata import language_name
from app.graph.state import ShoppingState
from app.prompts.understand_prompt import UNDERSTAND_SYSTEM_PROMPT
from app.schemas.understanding import QueryUnderstanding
from app.tools.currency import UnsupportedCurrencyError, convert_currency

# Used when the model classifies the message as general chat but leaves reply empty.
_FALLBACK_GENERAL_REPLY = {
    "vi": "Xin chào! Mình là trợ lý tư vấn mua laptop — bạn cần tìm laptop như thế nào?",
    "en": "Hi! I'm a laptop shopping assistant — ask me about laptops and I'll help you find one.",
}


def _budget_in_vnd(understanding: QueryUnderstanding) -> float | None:
    if understanding.budget is None:
        return None
    try:
        return convert_currency(understanding.budget, understanding.budget_currency)
    except UnsupportedCurrencyError:
        # Comparing against an unconverted foreign amount would be wrong; treat as no budget instead.
        emit("budget_dropped", "Unsupported budget currency", node="understand", status="warning",
             currency=understanding.budget_currency)
        return None


def understand_node(state: ShoppingState) -> dict:
    language = state.get("language")
    understanding = invoke_structured(
        QueryUnderstanding,
        [
            ("system", UNDERSTAND_SYSTEM_PROMPT.format(language=language_name(language))),
            ("human", state["query"]),
        ],
    )

    if not understanding.is_shopping_related:
        reply = understanding.reply or _FALLBACK_GENERAL_REPLY.get(language, _FALLBACK_GENERAL_REPLY["vi"])
        emit("intent_classified", "Query is general chat", node="understand", intent="general")
        return {"intent": "general", "general_reply": reply}

    budget = _budget_in_vnd(understanding)
    emit(
        "intent_classified",
        "Requirements extracted",
        node="understand",
        intent="shopping",
        budget=budget,
        purpose=understanding.purpose,
    )
    return {
        "intent": "shopping",
        "general_reply": None,
        "budget": budget,
        "purpose": understanding.purpose,
        "preferences": understanding.preferences,
        "constraints": understanding.constraints,
    }
