import time
from collections.abc import Callable
from functools import wraps

from langchain_core.callbacks import get_usage_metadata_callback

from app.core.events import emit


def _token_totals(usage_by_model: dict) -> dict[str, int]:
    return {
        "input_tokens": sum(usage.get("input_tokens", 0) for usage in usage_by_model.values()),
        "output_tokens": sum(usage.get("output_tokens", 0) for usage in usage_by_model.values()),
    }


def measured(name: str, node: Callable[[dict], dict]) -> Callable[[dict], dict]:
    """Wrap a graph node so each run reports its duration and LLM token usage as a `node_measured` event.

    The usage callback is bound to the current context, so it also counts model calls made deeper in
    the node, such as those inside the research agent's loop. A failed attempt is reported too, since
    a retried node spends tokens on every attempt.
    """

    @wraps(node)
    def run(state: dict) -> dict:
        started = time.perf_counter()
        failed = True
        with get_usage_metadata_callback() as usage:
            try:
                result = node(state)
                failed = False
                return result
            finally:
                duration_ms = round((time.perf_counter() - started) * 1000)
                emit("node_measured", f"{name} finished in {duration_ms} ms", node=name,
                     status="warning" if failed else "info", duration_ms=duration_ms, failed=failed,
                     **_token_totals(usage.usage_metadata))

    return run
