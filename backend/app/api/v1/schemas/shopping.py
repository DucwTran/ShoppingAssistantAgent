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
    quality_threshold: float
    evaluation_feedback: str | None
    general_reply: str | None = None


class ShoppingResponse(BaseModel):
    thread_id: str
    status: Literal["pending_approval", "done"]
    data: ShoppingResultData
