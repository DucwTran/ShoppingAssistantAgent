from pydantic import BaseModel, Field


class ShoppingRequirements(BaseModel):
    category: str = Field(description="Product category, e.g. 'laptop'")
    budget: float | None = Field(default=None, description="Budget in VND")
    purpose: list[str] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
