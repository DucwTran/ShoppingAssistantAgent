from pydantic import BaseModel

from app.schemas.product import Product


class CompareProductsArgs(BaseModel):
    products: list[Product]
