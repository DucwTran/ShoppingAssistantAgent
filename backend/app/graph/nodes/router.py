from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.router_prompt import ROUTER_SYSTEM_PROMPT
from app.schemas.router import SearchDecision


def router_node(state: ShoppingState) -> dict:
    decision = invoke_structured(
        SearchDecision,
        [
            ("system", ROUTER_SYSTEM_PROMPT),
            ("human", state["query"]),
        ],
    )

    emit(
        "router_decided",
        "Information sources selected",
        node="router",
        use_web=decision.use_web,
        use_rag=decision.use_rag,
        reason=decision.reason,
    )

    return {"use_web": decision.use_web, "use_rag": decision.use_rag}
