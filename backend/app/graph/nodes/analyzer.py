from app.core.events import emit
from app.core.llm import get_llm
from app.graph.state import ShoppingState
from app.prompts.analyzer_prompt import ANALYZER_SYSTEM_PROMPT
from app.schemas.requirements import ShoppingRequirements


def analyzer_node(state: ShoppingState) -> dict:
    llm = get_llm().with_structured_output(ShoppingRequirements)
    requirements = llm.invoke(
        [
            ("system", ANALYZER_SYSTEM_PROMPT),
            ("human", state["query"]),
        ]
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
