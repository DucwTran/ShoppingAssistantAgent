import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import timedelta

from fastapi import FastAPI
from langgraph.checkpoint.sqlite import SqliteSaver

from app.api.health import router as health_router
from app.api.middleware import add_cors, add_request_context, register_exception_handlers
from app.api.v1.routers.shopping import router as shopping_router
from app.core.checkpointer import open_checkpointer, prune_checkpoints
from app.core.config import settings
from app.core.logging import logger
from app.graph.graph import build_graph

_PRUNE_INTERVAL_SECONDS = 3600


def _prune(saver: SqliteSaver) -> None:
    max_age = timedelta(hours=settings.checkpoint_ttl_hours)
    try:
        deleted = prune_checkpoints(saver, max_age)
        if deleted:
            logger.info("Pruned %d conversations idle for more than %s", deleted, max_age)
    except Exception:  # noqa: BLE001 - a failed cleanup must not stop the server; retried next time
        logger.exception("Checkpoint pruning failed")


async def _prune_periodically(saver: SqliteSaver) -> None:
    """Prune hourly in a worker thread, so requests are not blocked.

    The connection is closed right after this task is cancelled at shutdown, so a prune already
    running in its thread is allowed to finish first: closing the connection under it crashes the process.
    """
    while True:
        await asyncio.sleep(_PRUNE_INTERVAL_SECONDS)
        job = asyncio.ensure_future(asyncio.to_thread(_prune, saver))
        try:
            await asyncio.shield(job)
        except asyncio.CancelledError:
            await job
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = settings.missing_required_keys()
    if missing and settings.app_env == "production":
        # Fail fast: a server that starts without its keys looks healthy but fails every query
        raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
    if missing:
        logger.warning("Missing configuration, queries will fail: %s", ", ".join(missing))
    with open_checkpointer() as checkpointer:
        _prune(checkpointer)  # before serving, so no request and no shutdown can race it
        app.state.checkpointer = checkpointer
        app.state.graph = build_graph(checkpointer)
        pruning = asyncio.create_task(_prune_periodically(checkpointer))
        try:
            yield
        finally:
            pruning.cancel()
            with suppress(asyncio.CancelledError):
                await pruning


app = FastAPI(title="AI Shopping Assistant API", lifespan=lifespan)

add_cors(app)
register_exception_handlers(app)
add_request_context(app)
app.include_router(shopping_router, prefix="/api/v1/shopping", tags=["shopping"])
app.include_router(health_router, prefix="/health", tags=["health"])
