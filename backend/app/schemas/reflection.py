from pydantic import BaseModel, Field


class ReflectionDecision(BaseModel):
    reflection_reason: str = Field(description="What is missing and what this attempt targets")
    refined_query: str = Field(min_length=1, description="A targeted query aimed at the identified gap")
