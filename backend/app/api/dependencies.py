from fastapi import Request


def get_graph(request: Request):
    """Return the compiled graph built once at process startup (see main.py's lifespan).

    It must stay a singleton: the graph owns the checkpointer connection, and every request has to
    see the same thread store or /resume would never find the state saved by /query.
    """
    return request.app.state.graph
