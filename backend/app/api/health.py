from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.rag.vectorstore import index_exists

router = APIRouter()


@router.get("/live")
def live() -> dict:
    """The process is up and serving requests; a failure here means it should be restarted."""
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request) -> JSONResponse:
    """Whether a query can succeed now, checked locally: no LLM or search call, so polling it costs no quota.

    Missing keys are not checked here: in production the server refuses to start without them.
    """
    checks = {
        "checkpointer": _checkpointer_ok(request),
        "knowledge_index": index_exists(),
    }
    is_ready = all(checks.values())
    return JSONResponse(status_code=200 if is_ready else 503,
                        content={"status": "ready" if is_ready else "not_ready", "checks": checks})


def _checkpointer_ok(request: Request) -> bool:
    try:
        with request.app.state.checkpointer.cursor(transaction=False) as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any failure means not ready; the check itself must not raise
        return False
