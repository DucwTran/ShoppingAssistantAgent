from pydantic import BaseModel, Field


class IntentDecision(BaseModel):
    is_shopping_related: bool
    reply: str | None = Field(default=None)
