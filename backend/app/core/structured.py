import json
from typing import Any, TypeVar

from pydantic import BaseModel

from app.core.llm import get_llm

T = TypeVar("T", bound=BaseModel)


def invoke_structured(schema: type[T], messages: list[tuple[str, str]], max_retries: int = 2) -> T:
    """Call the LLM with structured output, retrying a bounded number of times.

    LLM tool-calling occasionally omits a required field or returns a type the
    provider's schema validator rejects (non-deterministic generation) — retry
    rather than crash the graph on a single bad generation.
    """
    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            llm = get_llm().with_structured_output(schema)
            return llm.invoke(messages)
        except Exception as exc:  # noqa: BLE001 - deliberately broad, bounded by max_retries
            last_error = exc
    raise last_error


def invoke_agent(agent: Any, messages: list[tuple[str, str]], schema: type[T], max_retries: int = 2) -> T:
    """Run a create_agent tool-calling loop, then extract structured output from its final answer.

    Some models (seen with Ollama) don't reliably call a forced "final answer" tool and just
    reply in plain text once they consider the task done — instead of depending on that, run the
    tool loop with no response_format at all and let it produce a plain-text final answer, then
    run a separate extraction call on ONLY that final text (not the full tool-call trace, which
    confuses smaller models into pulling raw tool JSON into the wrong fields).

    The extraction call uses method="json_mode" with the schema spelled out in the prompt rather
    than with_structured_output()'s default schema-constrained decoding: on a small local model,
    strict grammar-constrained decoding was observed to produce technically-valid but empty
    output (e.g. products=[]) for a list-of-objects schema, while plain JSON generation guided by
    an explicit schema description reliably filled it in. This also sidesteps providers (e.g.
    Groq) that reject combining tool-calling with JSON-mode structured output in one request,
    since this call has no tools bound at all.
    """
    result = agent.invoke({"messages": messages})
    final_text = result["messages"][-1].content

    prompt = (
        f"Extract the information below into JSON matching this schema:\n{json.dumps(schema.model_json_schema())}"
        f"\n\nText:\n{final_text}\n\nRespond with ONLY the JSON object."
    )

    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            structured_llm = get_llm().with_structured_output(schema, method="json_mode")
            return structured_llm.invoke([("human", prompt)])
        except Exception as exc:  # noqa: BLE001 - deliberately broad, bounded by max_retries
            last_error = exc
    raise last_error
