from pydantic import BaseModel, Field


class ConvertCurrencyArgs(BaseModel):
    amount: float = Field(ge=0)
    from_currency: str
    to_currency: str = "VND"
