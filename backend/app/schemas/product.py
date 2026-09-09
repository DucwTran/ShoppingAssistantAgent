from pydantic import BaseModel, Field


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
    products: list[Product] = Field(default_factory=list)
