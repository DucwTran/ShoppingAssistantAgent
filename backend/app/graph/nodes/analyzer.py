from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.analyzer_prompt import ANALYZER_SYSTEM_PROMPT
from app.schemas.requirements import ShoppingRequirements


def analyzer_node(state: ShoppingState) -> dict:
    requirements = invoke_structured(
        ShoppingRequirements,
        [
            ("system", ANALYZER_SYSTEM_PROMPT),
            ("human", state["query"]),
        ],
    )

    emit(
        "analyzer_done",
        "Requirements extracted",
        node="analyzer",
        budget=requirements.budget,
        purpose=requirements.purpose,
    )

    return {
        "budget": requirements.budget,
        "purpose": requirements.purpose,
        "preferences": requirements.preferences,
        "constraints": requirements.constraints,
    }
