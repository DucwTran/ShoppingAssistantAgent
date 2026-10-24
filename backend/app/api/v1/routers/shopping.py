import json
import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from langgraph.types import Command

from app.api.dependencies import get_graph
from app.api.rate_limit import rate_limit
from app.api.v1.schemas.shopping import QueryRequest, ResumeRequest, ShoppingResponse, ShoppingResultData
from app.core.errors import to_app_error
from app.guards.input_guard import validate_input

router = APIRouter(dependencies=[Depends(rate_limit)])


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _response_from_state(graph, thread_id: str) -> ShoppingResponse:
    """Build the response from the persisted thread state - the same path for JSON and streaming endpoints."""
    snapshot = graph.get_state(_config(thread_id))

    if snapshot.interrupts:
        data = ShoppingResultData(**snapshot.interrupts[0].value)
        return ShoppingResponse(thread_id=thread_id, status="pending_approval", data=data)

    values = snapshot.values
    data = ShoppingResultData(recommendation=values.get("recommendation"), general_reply=values.get("general_reply"))
    status = "rejected" if values.get("human_approval") is False else "done"
    return ShoppingResponse(thread_id=thread_id, status=status, data=data)


def _conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def _existing_snapshot(graph, thread_id: str):
    snapshot = graph.get_state(_config(thread_id))
    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail={"code": "thread_not_found", "message": f"No thread with id '{thread_id}'."},
        )
    return snapshot


def _unfinished_snapshot(graph, thread_id: str):
    snapshot = _existing_snapshot(graph, thread_id)
    if not snapshot.next:
        raise _conflict("thread_already_finished", f"Thread '{thread_id}' has already finished.")
    return snapshot


def _thread_for_question(graph, thread_id: str | None) -> str:
    """A new conversation, or a finished one continued with a follow-up question."""
    if thread_id is None:
        return str(uuid.uuid4())
    if _existing_snapshot(graph, thread_id).next:
        raise _conflict("conversation_busy",
                        f"Thread '{thread_id}' is waiting for a decision or a retry; finish that turn first.")
    return thread_id


def _resume_command(graph, thread_id: str, body: ResumeRequest) -> Command:
    """The human decision, accepted only while the thread is paused for it."""
    if not _unfinished_snapshot(graph, thread_id).interrupts:
        raise _conflict("not_awaiting_decision", f"Thread '{thread_id}' is not waiting for a decision.")
    # Feedback reaches the prompts like a query does, so it passes the same guard
    feedback = validate_input(body.feedback, label="Feedback") if body.feedback and body.feedback.strip() else None
    return Command(resume={"approved": body.approved, "feedback": feedback})


def _ensure_failed(graph, thread_id: str) -> None:
    """A run that stopped on an error is checkpointed at the step that failed; only such a thread can be retried."""
    if _unfinished_snapshot(graph, thread_id).interrupts:
        raise _conflict("nothing_to_retry", f"Thread '{thread_id}' is waiting for a decision, not a retry.")


def _invoke(graph, graph_input, thread_id: str) -> ShoppingResponse:
    try:
        graph.invoke(graph_input, _config(thread_id))
    except Exception as exc:
        raise to_app_error(exc, thread_id) from exc
    return _response_from_state(graph, thread_id)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _stream_run(graph, graph_input, thread_id: str) -> Iterator[str]:
    """Run the graph and yield SSE frames: `progress` per node event, then one `result` or `error`.

    A sync generator: Starlette iterates it in a worker thread, so the sync graph and checkpointer work as-is.
    Errors after the 200 status line is sent can only be reported in-band, as an `error` frame carrying the
    status the JSON endpoint would have returned and the thread_id to pass to /retry.
    """
    try:
        for chunk in graph.stream(graph_input, _config(thread_id), stream_mode="custom"):
            yield _sse("progress", chunk)
        yield _sse("result", _response_from_state(graph, thread_id).model_dump())
    except Exception as exc:  # noqa: BLE001 - reported to the client in-band, classified and logged
        error = to_app_error(exc, thread_id)
        yield _sse("error", {"status": error.status, "thread_id": thread_id, **error.body()})


def _event_stream(frames: Iterator[str]) -> StreamingResponse:
    return StreamingResponse(frames, media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@router.post("/query", response_model=ShoppingResponse)
def query(body: QueryRequest, graph=Depends(get_graph)) -> ShoppingResponse:
    query_text = validate_input(body.query)
    return _invoke(graph, {"query": query_text}, _thread_for_question(graph, body.thread_id))


@router.post("/resume/{thread_id}", response_model=ShoppingResponse)
def resume(thread_id: str, body: ResumeRequest, graph=Depends(get_graph)) -> ShoppingResponse:
    return _invoke(graph, _resume_command(graph, thread_id, body), thread_id)


@router.post("/retry/{thread_id}", response_model=ShoppingResponse)
def retry(thread_id: str, graph=Depends(get_graph)) -> ShoppingResponse:
    # None as input makes LangGraph continue from the last checkpoint, i.e. re-run the failed step.
    _ensure_failed(graph, thread_id)
    return _invoke(graph, None, thread_id)


@router.post("/query/stream")
def query_stream(body: QueryRequest, graph=Depends(get_graph)) -> StreamingResponse:
    # Validated before streaming starts so a bad query still gets a proper 400, not an in-band error.
    query_text = validate_input(body.query)
    thread_id = _thread_for_question(graph, body.thread_id)
    return _event_stream(_stream_run(graph, {"query": query_text}, thread_id))


@router.post("/resume/{thread_id}/stream")
def resume_stream(thread_id: str, body: ResumeRequest, graph=Depends(get_graph)) -> StreamingResponse:
    return _event_stream(_stream_run(graph, _resume_command(graph, thread_id, body), thread_id))


@router.post("/retry/{thread_id}/stream")
def retry_stream(thread_id: str, graph=Depends(get_graph)) -> StreamingResponse:
    _ensure_failed(graph, thread_id)
    return _event_stream(_stream_run(graph, None, thread_id))
