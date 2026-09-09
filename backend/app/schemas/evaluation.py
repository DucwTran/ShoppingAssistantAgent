from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Overall recommendation quality, 0 to 1")
    passed: bool = Field(description="Whether the recommendation meets the quality bar")
    feedback: str = Field(description="What is missing or weak, stated concretely")
