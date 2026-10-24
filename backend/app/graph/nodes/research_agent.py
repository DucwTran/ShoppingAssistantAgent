import json
import re
from functools import lru_cache

from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware, ToolCallLimitMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from app.core.config import settings
from app.core.events import emit
from app.core.llm import chat_model, key_rotation_middleware
from app.graph.state import ShoppingState, question_of, requirements_of
from app.prompts.language import language_name
from app.prompts.research_agent_prompt import RESEARCH_AGENT_SYSTEM_PROMPT
from app.tools.agent_tools import RESEARCH_TOOLS, search_knowledge_base, web_search

_NODE = "research_agent"


@lru_cache(maxsize=1)
def _research_agent():
    return create_agent(
        # key_rotation_middleware swaps in the model for the key in use on every call
        model=chat_model(settings.gemini_api_keys[0]),
        tools=RESEARCH_TOOLS,
        system_prompt=RESEARCH_AGENT_SYSTEM_PROMPT,
        middleware=[
            key_rotation_middleware,
            PIIMiddleware("email", strategy="redact"),
            ToolCallLimitMiddleware(run_limit=settings.research_tool_call_limit, exit_behavior="end"),
        ],
        # The agent's scratch messages are not worth persisting; only the node's output enters graph state.
        checkpointer=False,
    )


def _instruction(state: ShoppingState) -> str:
    payload = {
        "question": question_of(state),
        "language": language_name(state.get("language")),
        "requirements": requirements_of(state),
    }
    if state.get("research_hint"):
        payload["previous_recommendation_rejected_search_for"] = state["research_hint"]
    return json.dumps(payload, ensure_ascii=False)


def _run_agent(state: ShoppingState) -> list:
    """Stream the agent so each tool call reaches the client as a progress event while it happens."""
    messages: list = []
    for step in _research_agent().stream({"messages": [("human", _instruction(state))]}, stream_mode="values"):
        for message in step["messages"][len(messages):]:
            if isinstance(message, AIMessage):
                for call in message.tool_calls:
                    emit("tool_called", f"Calling {call['name']}", node=_NODE, tool=call["name"], args=call["args"])
            elif isinstance(message, ToolMessage):
                count = len(message.artifact) if isinstance(message.artifact, list) else 0
                emit("tool_returned", f"{message.name} returned {count} results", node=_NODE,
                     tool=message.name, results=count)
        messages = step["messages"]
    return messages


def _collect_artifacts(messages: list) -> tuple[list[dict], list[dict]]:
    web_results: list[dict] = []
    docs: list[dict] = []
    for message in messages:
        if isinstance(message, ToolMessage) and isinstance(message.artifact, list):
            if message.name == web_search.name:
                web_results.extend(message.artifact)
            elif message.name == search_knowledge_base.name:
                docs.extend(message.artifact)
    return web_results, docs


def _fallback_query(state: ShoppingState) -> str:
    """The rejection hint or the question, plus the budget in millions VND unless the text already states it."""
    text = state.get("research_hint") or question_of(state)
    if state.get("budget"):
        millions = f"{state['budget'] / 1_000_000:.0f}"
        if not re.search(rf"(?<!\d){millions}(?!\d)", text):
            text = f"{text} dưới {millions} triệu"
    return text[:400]


def _fallback_research(state: ShoppingState) -> tuple[list[dict], list[dict]]:
    """Deterministic search used when the agent produced nothing (or failed): same tools, fixed queries."""
    emit("research_fallback", "Agent found nothing; running a direct search", node=_NODE, status="warning")
    _, web_results = web_search.func(query=_fallback_query(state), max_results=settings.web_search_max_results)
    _, docs = search_knowledge_base.func(query=question_of(state)[:400])
    return web_results, docs


def _dedupe(items: list[dict], key: str) -> list[dict]:
    seen: set = set()
    unique = []
    for item in items:
        if item.get(key) not in seen:
            seen.add(item.get(key))
            unique.append(item)
    return unique


def research_agent_node(state: ShoppingState) -> dict:
    try:
        web_results, docs = _collect_artifacts(_run_agent(state))
    except Exception as exc:  # noqa: BLE001 - an agent failure degrades to the direct search, not a 500
        emit("research_agent_failed", "Research agent failed", node=_NODE, status="warning", error=repr(exc))
        web_results, docs = [], []

    if not web_results and not docs:
        web_results, docs = _fallback_research(state)

    if state.get("research_hint"):
        # A follow-up search after a rejection widens the pool instead of discarding earlier candidates.
        web_results = web_results + state.get("web_results", [])
        docs = docs + state.get("retrieved_docs", [])

    web_results = _dedupe(web_results, "url")
    docs = _dedupe(docs, "text")
    status = "ok" if web_results or docs else "empty"

    emit(
        "research_done",
        "Research finished",
        node=_NODE,
        status="info" if status == "ok" else "warning",
        web_results=len(web_results),
        retrieved_docs=len(docs),
    )
    return {"web_results": web_results, "retrieved_docs": docs, "research_status": status}
