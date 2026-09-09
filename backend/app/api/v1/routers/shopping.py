import uuid

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command

from app.api.dependencies import get_graph
from app.api.v1.schemas.shopping import QueryRequest, ResumeRequest, ShoppingResponse, ShoppingResultData

router = APIRouter()


def _response_from_invoke_result(thread_id: str, result: dict) -> ShoppingResponse:
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        data = ShoppingResultData(**payload)
        return ShoppingResponse(thread_id=thread_id, status="pending_approval", data=data)

    data = ShoppingResultData(
        recommendation=result.get("recommendation"),
        quality_score=result.get("quality_score"),
        evaluation_feedback=result.get("evaluation_feedback"),
        reflection_count=result.get("reflection_count", 0),
    )
    return ShoppingResponse(thread_id=thread_id, status="done", data=data)


@router.post("/query", response_model=ShoppingResponse)
def query(body: QueryRequest, graph=Depends(get_graph)) -> ShoppingResponse:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke({"query": body.query}, config)
    return _response_from_invoke_result(thread_id, result)


@router.post("/resume/{thread_id}", response_model=ShoppingResponse)
def resume(thread_id: str, body: ResumeRequest, graph=Depends(get_graph)) -> ShoppingResponse:
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail={"code": "thread_not_found", "message": f"No thread with id '{thread_id}'."},
        )
    if not snapshot.next:
        raise HTTPException(
            status_code=409,
            detail={"code": "thread_already_finished", "message": f"Thread '{thread_id}' has no pending approval."},
        )

    result = graph.invoke(Command(resume={"approved": body.approved, "feedback": body.feedback}), config)
    return _response_from_invoke_result(thread_id, result)
