from typing import Callable, TypeVar

from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, ValidationError

from app.core.llm import chat_model, with_key_rotation

T = TypeVar("T", bound=BaseModel)


def _generate(schema: type[T], messages: list[tuple[str, str]]) -> T | None:
    return with_key_rotation(lambda key: chat_model(key).with_structured_output(schema).invoke(messages))


def invoke_structured(
    schema: type[T],
    messages: list[tuple[str, str]],
    check: Callable[[T], None] | None = None,
    max_retries: int = 2,
) -> T:
    """Call the LLM with structured output, retrying a bounded number of times on bad generations.

    Only generation-quality failures are retried here: a missing/invalid field, unparsable output,
    or a `check` callback rejecting a value that depends on runtime data (e.g. an id that must
    exist in the candidate list). Key-level failures are handled by the key rotation; transport
    failures (timeouts, connection errors, 5xx) propagate so the graph node's RetryPolicy handles them.
    """
    last_error: Exception | None = None
    for _ in range(max_retries + 1):
        try:
            result = _generate(schema, messages)
            if result is None:
                raise OutputParserException("Model returned no structured output.")
            if check:
                check(result)
            return result
        except (ValidationError, OutputParserException, ValueError) as exc:
            last_error = exc
    raise last_error
