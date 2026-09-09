from app.core.logging import log_event


def emit(event_type: str, message: str, node: str = "graph", **data) -> None:
    """Single entry point for node progress events.

    Currently writes to the console logger; a streaming transport (e.g. SSE)
    can be added here later without changing any call site.
    """
    log_event(node=node, event=event_type, status="info", message=message, **data)
