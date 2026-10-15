from typing import Literal

from pydantic import BaseModel

# pending_approval: waiting for POST /resume; done: approved or general-chat reply;
# rejected: the rejection cap was reached, so the last recommendation was never approved.
ConversationStatus = Literal["pending_approval", "done", "rejected"]


class QueryRequest(BaseModel):
    query: str


class ResumeRequest(BaseModel):
    approved: bool
    feedback: str | None = None


class ShoppingResultData(BaseModel):
    recommendation: dict | None
    quality_score: float | None
    quality_threshold: float
    evaluation_feedback: str | None
    general_reply: str | None = None


class ShoppingResponse(BaseModel):
    thread_id: str
    status: ConversationStatus
    data: ShoppingResultData
