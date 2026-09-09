from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_list


class Product(BaseModel):
    name: str
    price: float | str = Field(default="unknown", description="Price in VND, or 'unknown'")
    currency: str = "VND"
    cpu: str = "unknown"
    gpu: str = "unknown"
    ram: str = "unknown"
    storage: str = "unknown"
    url: str = "unknown"
    source_name: str = "unknown"


class ProductList(BaseModel):
    products: Annotated[list[Product] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
