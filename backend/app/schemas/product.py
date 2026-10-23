import re
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field

# "24.990.000", "24,990,000" - thousands-grouped integer, as Vietnamese retailers write prices
_GROUPED_INT = re.compile(r"^\d{1,3}([.,]\d{3})+$")


def _price_or_none(value):
    """Accept a number or a price string; anything unparsable ("unknown", "Liên hệ", "") means no price."""
    if value is None or isinstance(value, (int, float)):
        return value
    text = re.sub(r"[^\d.,]", "", str(value))
    if _GROUPED_INT.match(text):
        return float(re.sub(r"[.,]", "", text))
    try:
        return float(text.replace(",", ""))
    except ValueError:
        return None


class Product(BaseModel):
    name: str = Field(min_length=1)
    price: Annotated[float | None, BeforeValidator(_price_or_none)] = Field(
        default=None, description="Numeric price exactly as listed in the source, null if not stated"
    )
    currency: str = Field(default="VND", description="3-letter currency code of price")
    cpu: str = "unknown"
    gpu: str = "unknown"
    ram: str = "unknown"
    storage: str = "unknown"
    source_url: str = Field(default="unknown", description="url of the search result this product was taken from")
