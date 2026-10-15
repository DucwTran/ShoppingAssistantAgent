from pydantic import BaseModel, Field


class FeedbackDecision(BaseModel):
    needs_new_products: bool = Field(description="True if satisfying the feedback needs products not in the current list")
    research_hint: str | None = Field(default=None, description="What to search for next, when needs_new_products")
