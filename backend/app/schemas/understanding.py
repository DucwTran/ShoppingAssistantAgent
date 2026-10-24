from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_dict, none_to_list


class QueryUnderstanding(BaseModel):
    is_shopping_related: bool
    standalone_query: str | None = Field(
        default=None,
        description="The current message rewritten to be understood without the conversation history; "
                    "the message itself when it needs no context",
    )
    reply: str | None = Field(default=None, description="Friendly reply, only when is_shopping_related is false")
    budget: float | None = Field(default=None, description="Maximum budget amount as a number")
    budget_currency: str = Field(default="VND", description="3-letter currency code of budget")
    purpose: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
    preferences: Annotated[dict | None, BeforeValidator(none_to_dict)] = Field(default_factory=dict)
    constraints: Annotated[list[str] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
