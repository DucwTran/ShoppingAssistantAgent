import logging
import sys

from langgraph.config import get_config

logger = logging.getLogger("shopping_assistant")
logger.setLevel(logging.INFO)

if not logger.handlers:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)


def _thread_id() -> str | None:
    """thread_id of the graph run this code executes in, or None outside a graph run."""
    try:
        return get_config().get("configurable", {}).get("thread_id")
    except RuntimeError:
        return None


def log_event(node: str, event: str, status: str = "info", **data) -> None:
    thread_id = _thread_id()
    extra = " ".join(f"{k}={v}" for k, v in data.items())
    line = f"[thread={thread_id[:8] if thread_id else '-'}] [node={node}] [event={event}] {extra}".rstrip()
    (logger.warning if status == "warning" else logger.info)(line)
