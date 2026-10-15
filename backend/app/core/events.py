from langgraph.config import get_stream_writer

from app.core.logging import log_event


def emit(event_type: str, message: str, node: str = "graph", status: str = "info", **data) -> None:
    """Single entry point for node progress events.

    Always logs; additionally pushes the event to LangGraph's "custom" stream so the SSE endpoints
    can forward it to the client. Outside a graph run (CLI helpers, unit tests calling a node
    function directly) there is no stream writer and the event is only logged.
    """
    log_event(node=node, event=event_type, status=status, message=message, **data)
    try:
        writer = get_stream_writer()
    except (RuntimeError, KeyError):  # no runnable context / runnable context outside a graph
        return
    writer({"event": event_type, "node": node, "status": status, "message": message, **data})
