from fastapi import Request


def get_graph(request: Request):
    """Return the compiled graph built once at process startup (see main.py's lifespan).

    Unlike core/checkpointer.py's get_checkpointer(), this must stay a singleton — the
    checkpointer it wraps only lives in memory, so building a fresh graph per call would
    make every request its own isolated thread store and /resume would never find prior state.
    """
    return request.app.state.graph
