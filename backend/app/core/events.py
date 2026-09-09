from app.core.logging import log_event


def emit(event_type: str, message: str, node: str = "graph", **data) -> None:
    """Emit a progress event.

    Phase 1-4: writes to the console logger only.
    Phase 5 will extend this to also push the event onto a per-thread_id
    SSE queue, without requiring any change in the nodes that call emit().
    """
    log_event(node=node, event=event_type, status="info", message=message, **data)
