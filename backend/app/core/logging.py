import logging
import sys

logger = logging.getLogger("shopping_assistant")
logger.setLevel(logging.INFO)

if not logger.handlers:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", "%H:%M:%S"))
    logger.addHandler(handler)


def log_event(node: str, event: str, status: str = "info", **data) -> None:
    extra = " ".join(f"{k}={v}" for k, v in data.items())
    logger.info(f"[node={node}] [event={event}] [status={status}] {extra}".rstrip())
