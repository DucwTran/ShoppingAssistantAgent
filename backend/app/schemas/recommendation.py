from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_list

NO_PRODUCT = "N/A"


class RecommendationChoice(BaseModel):
    """What the LLM decides; product facts are filled in from the candidate list by code."""

    product_id: int | None = Field(description="id of the chosen candidate, null if no candidate fits or none exist")
    alternative_id: int | None = Field(default=None, description="id of a second-best candidate, or null")
    why_it_fits: Annotated[list[str], BeforeValidator(none_to_list), Field(min_length=1)]
    tradeoffs: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class Recommendation(BaseModel):
    product_name: str = Field(min_length=1, description=f'"{NO_PRODUCT}" when there is no single product to recommend')
    price: float | None = None
    currency: str | None = None
    url: str | None = None
    why_it_fits: Annotated[list[str], BeforeValidator(none_to_list), Field(min_length=1)]
    tradeoffs: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    alternative: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
