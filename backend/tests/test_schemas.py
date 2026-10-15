import pytest
from pydantic import ValidationError

from app.schemas.evaluation import PurposeJudgement
from app.schemas.product import Product
from app.schemas.recommendation import Recommendation, RecommendationChoice
from app.schemas.understanding import QueryUnderstanding


def test_query_understanding_general_chat():
    understanding = QueryUnderstanding(is_shopping_related=False, reply="Hi!")
    assert understanding.budget is None
    assert understanding.purpose == []


def test_query_understanding_coerces_nulls_to_empty():
    understanding = QueryUnderstanding(is_shopping_related=True, purpose=None, preferences=None, constraints=None)
    assert understanding.purpose == []
    assert understanding.preferences == {}
    assert understanding.budget_currency == "VND"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (22_990_000, 22_990_000),
        ("22.990.000đ", 22_990_000),
        ("22,990,000 VND", 22_990_000),
        ("1299.99", 1299.99),
        ("unknown", None),
        ("Liên hệ", None),
        (None, None),
    ],
)
def test_product_price_parsing(raw, expected):
    assert Product(name="A", price=raw).price == expected


def test_product_requires_name():
    with pytest.raises(ValidationError):
        Product(name="")


def test_recommendation_choice_requires_reasoning():
    with pytest.raises(ValidationError):
        RecommendationChoice(product_id=0, why_it_fits=[], confidence=0.5)


def test_recommendation_rejects_out_of_range_confidence():
    with pytest.raises(ValidationError):
        Recommendation(product_name="A", why_it_fits=["x"], confidence=1.5)


def test_purpose_judgement_bounds():
    assert PurposeJudgement(purpose_fit=0.7, feedback="ok").purpose_fit == 0.7
    with pytest.raises(ValidationError):
        PurposeJudgement(purpose_fit=-0.1, feedback="")
