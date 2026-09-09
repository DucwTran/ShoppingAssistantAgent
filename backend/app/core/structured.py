from typing import TypeVar

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
