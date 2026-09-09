import pytest
from pydantic import ValidationError

from app.schemas.requirements import ShoppingRequirements


def test_shopping_requirements_minimal():
    req = ShoppingRequirements(category="laptop")
    assert req.category == "laptop"
    assert req.budget is None
    assert req.purpose == []


def test_shopping_requirements_full():
    req = ShoppingRequirements(
        category="laptop",
        budget=25_000_000,
        purpose=["AI development", "gaming"],
        preferences={"portability": "high"},
        constraints=[],
    )
    assert req.budget == 25_000_000
    assert "gaming" in req.purpose


def test_shopping_requirements_requires_category():
    with pytest.raises(ValidationError):
        ShoppingRequirements()
