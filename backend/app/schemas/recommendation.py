from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    product_name: str
    price: float | str = "unknown"
    why_it_fits: list[str] = Field(default_factory=list)
    tradeoffs: list[str] = Field(default_factory=list)
    alternative: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
