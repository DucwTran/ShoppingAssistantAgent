from pydantic import BaseModel

from app.schemas.product import Product


class ScoreProductSpecArgs(BaseModel):
    product: Product
    budget: float | None = None
