import json

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, ToolCallLimitMiddleware

from app.core.events import emit
from app.core.llm import get_llm
from app.core.structured import invoke_agent
from app.graph.state import ShoppingState
from app.prompts.research_agent_prompt import RESEARCH_AGENT_SYSTEM_PROMPT
from app.schemas.research import ResearchOutput
from app.tools.agent_tools import RESEARCH_TOOLS
from app.tools.currency import UnsupportedCurrencyError
from app.tools.registry import TOOLS_BY_NAME

# No response_format here — the tool-calling loop runs free-form, then invoke_agent()
# extracts ResearchOutput from the resulting conversation as a separate step (see its docstring).
_research_agent = create_agent(
    model=get_llm(),
    tools=RESEARCH_TOOLS,
    system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
    middleware=[
        PIIMiddleware("email", strategy="redact"),
        ToolCallLimitMiddleware(run_limit=4, exit_behavior="end"),
    ],
)


def _to_vnd(product: dict) -> dict:
    if product["currency"].upper() == "VND" or not isinstance(product["price"], (int, float)):
        return product
    try:
        product["price"] = TOOLS_BY_NAME["convert_currency"].run(
            amount=product["price"], from_currency=product["currency"], to_currency="VND"
        )
        product["currency"] = "VND"
    except UnsupportedCurrencyError:
        pass
    return product


def _build_instruction(state: ShoppingState) -> str:
    payload = {
        "question": state["query"],
        "requirements": {
            "budget": state.get("budget"),
            "purpose": state.get("purpose", []),
            "preferences": state.get("preferences", {}),
            "constraints": state.get("constraints", []),
        },
    }
    if state.get("reflection_count", 0) > 0 and state.get("search_query"):
        payload["previous_gap"] = state.get("reflection_reason")
        payload["refined_focus"] = state["search_query"]
    return json.dumps(payload, ensure_ascii=False)


def research_agent_node(state: ShoppingState) -> dict:
    instruction = _build_instruction(state)
    output: ResearchOutput = invoke_agent(_research_agent, [("human", instruction)], ResearchOutput)

    # The prompt asks for at most 6, but smaller models don't always follow that
    # instruction reliably - enforce the cap here rather than trust it blindly.
    products = [_to_vnd(p.model_dump()) for p in output.products[:6]]

    emit(
        "research_done",
        "Research agent gathered products/knowledge",
        node="research_agent",
        products=len(products),
        retrieved_docs=len(output.retrieved_docs),
    )

    return {"products": products, "retrieved_docs": output.retrieved_docs}
