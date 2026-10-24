import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone

from langgraph.config import get_config

from app.core.config import settings

# Set per HTTP request by the request-context middleware; copied into worker threads and graph nodes
# with the rest of the context, so every line logged while serving a request carries its id.
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

logger = logging.getLogger("shopping_assistant")
logger.setLevel(logging.INFO)


class _ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        if not hasattr(record, "fields"):
            record.fields = {}
        return True


class _JsonFormatter(logging.Formatter):
    """One JSON object per line, for log collectors: fixed keys first, then the event's own fields."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": record.request_id,
            "message": record.getMessage(),
            **record.fields,
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False, default=str)


class _TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = super().format(record)
        return f"[req={record.request_id[:8]}] {line}" if record.request_id else line


def _handler() -> logging.Handler:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_ContextFilter())
    handler.setFormatter(_JsonFormatter() if settings.log_format == "json"
                         else _TextFormatter("[%(asctime)s] %(levelname)s %(message)s", "%H:%M:%S"))
    return handler


if not logger.handlers:
    logger.addHandler(_handler())
    if settings.log_format == "json":
        # Uvicorn's startup and error lines go out in the same format, so the stream stays parseable
        for name in ("uvicorn", "uvicorn.error"):
            logging.getLogger(name).handlers = [_handler()]
            logging.getLogger(name).propagate = False


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
    fields = {"message": event, "event": event, "node": node, "thread_id": thread_id, **data}
    (logger.warning if status == "warning" else logger.info)(line, extra={"fields": fields})
