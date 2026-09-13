from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.intent_prompt import INTENT_SYSTEM_PROMPT
from app.schemas.intent import IntentDecision

# Fallback used when the model classifies the message as general chat but leaves reply
# empty (observed with smaller local models that don't reliably fill every field).
_FALLBACK_GENERAL_REPLY = "Hi! I'm a laptop shopping assistant — ask me about laptops and I'll help you find one."


def intent_node(state: ShoppingState) -> dict:
    decision = invoke_structured(
        IntentDecision,
        [
            ("system", INTENT_SYSTEM_PROMPT),
            ("human", state["query"]),
        ],
    )

    intent = "shopping" if decision.is_shopping_related else "general"
    general_reply = decision.reply or (_FALLBACK_GENERAL_REPLY if intent == "general" else None)

    emit(
        "intent_classified",
        "Query intent classified",
        node="intent",
        intent=intent,
    )

    return {"intent": intent, "general_reply": general_reply}
