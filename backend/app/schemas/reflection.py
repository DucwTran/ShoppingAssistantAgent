from pydantic import BaseModel, Field


class ReflectionDecision(BaseModel):
    reflection_reason: str = Field(description="What is missing and what this attempt targets")
    use_web: bool = Field(description="Whether to search the web again with the refined query")
    use_rag: bool = Field(description="Whether to retrieve from the knowledge base again with the refined query")
    refined_query: str = Field(min_length=1, description="A targeted query aimed at the identified gap")
