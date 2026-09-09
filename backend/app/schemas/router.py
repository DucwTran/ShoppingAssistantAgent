from pydantic import BaseModel, Field


class SearchDecision(BaseModel):
    use_web: bool = Field(description="Whether current/external product info (prices, availability) is needed")
    use_rag: bool = Field(description="Whether stable domain knowledge (hardware concepts) is needed")
    reason: str
