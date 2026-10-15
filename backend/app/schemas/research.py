from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

from app.schemas._common import none_to_list
from app.schemas.product import Product


class ProductExtraction(BaseModel):
    products: Annotated[list[Product] | None, BeforeValidator(none_to_list)] = Field(default_factory=list)
