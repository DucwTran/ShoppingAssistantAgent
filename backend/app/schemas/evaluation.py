from pydantic import BaseModel, Field


class PurposeJudgement(BaseModel):
    purpose_fit: float = Field(ge=0.0, le=1.0, description="How well the recommendation serves the user's stated purpose")
    feedback: str = Field(description="The single most important concrete gap, or briefly why it is solid")
