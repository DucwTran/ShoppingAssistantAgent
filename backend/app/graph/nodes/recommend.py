import json

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, ToolCallLimitMiddleware

from app.core.events import emit
from app.core.llm import get_llm
from app.core.structured import invoke_agent
from app.graph.state import ShoppingState
from app.prompts.recommend_prompt import RECOMMEND_SYSTEM_PROMPT
from app.schemas.recommendation import Recommendation
from app.tools.agent_tools import RECOMMEND_TOOLS

# No response_format here — the tool-calling loop runs free-form, then invoke_agent()
# extracts Recommendation from the resulting conversation as a separate step (see its docstring).
_recommend_agent = create_agent(
    model=get_llm(),
    tools=RECOMMEND_TOOLS,
    system_prompt=RECOMMEND_SYSTEM_PROMPT,
    middleware=[
        PIIMiddleware("email", strategy="redact"),
        ToolCallLimitMiddleware(run_limit=8, exit_behavior="end"),
    ],
)


def recommend_node(state: ShoppingState) -> dict:
    payload = {
        "question": state["query"],
        "requirements": {
            "budget": state.get("budget"),
            "purpose": state.get("purpose", []),
            "preferences": state.get("preferences", {}),
            "constraints": state.get("constraints", []),
        },
        "products": state.get("products", []),
        "knowledge": state.get("retrieved_docs", []),
        "human_feedback": state.get("human_feedback"),
    }

    recommendation: Recommendation = invoke_agent(
        _recommend_agent, [("human", json.dumps(payload, ensure_ascii=False))], Recommendation
    )

    emit(
        "recommend_done",
        "Recommendation generated",
        node="recommend",
        product=recommendation.product_name,
        confidence=recommendation.confidence,
    )

    return {"recommendation": recommendation.model_dump()}
