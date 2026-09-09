from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_dict, none_to_list


class ShoppingRequirements(BaseModel):
    category: str = Field(description="Product category, e.g. 'laptop'")
    budget: float | None = Field(default=None, description="Budget in VND")
    purpose: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    preferences: Annotated[dict | None, BeforeValidator(none_to_dict)] = Field(default_factory=dict)
    constraints: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
