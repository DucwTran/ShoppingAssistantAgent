from typing import Literal

from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str


class ResumeRequest(BaseModel):
    approved: bool
    feedback: str | None = None


class ShoppingResultData(BaseModel):
    recommendation: dict | None
    quality_score: float | None
    evaluation_feedback: str | None
    reflection_count: int = 0
    general_reply: str | None = None


class ShoppingResponse(BaseModel):
    thread_id: str
    status: Literal["pending_approval", "done"]
    data: ShoppingResultData
