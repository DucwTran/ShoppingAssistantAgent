from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_list


class Recommendation(BaseModel):
    product_name: str
    price: float | str = "unknown"
    why_it_fits: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    tradeoffs: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    alternative: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
