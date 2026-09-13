import pytest
from pydantic import ValidationError

from app.schemas.evaluation import EvaluationResult
from app.schemas.intent import IntentDecision
from app.schemas.reflection import ReflectionDecision
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


def test_evaluation_result_accepts_valid_score():
    result = EvaluationResult(score=0.7, passed=True, feedback="Solid match on budget and purpose.")
    assert result.score == 0.7


def test_evaluation_result_rejects_score_above_one():
    with pytest.raises(ValidationError):
        EvaluationResult(score=1.5, passed=True, feedback="")


def test_evaluation_result_rejects_negative_score():
    with pytest.raises(ValidationError):
        EvaluationResult(score=-0.1, passed=False, feedback="")


def test_reflection_decision_accepts_valid_input():
    decision = ReflectionDecision(
        reflection_reason="Missing battery life info",
        refined_query="battery life comparison for top candidates",
    )
    assert decision.refined_query == "battery life comparison for top candidates"


def test_reflection_decision_rejects_empty_refined_query():
    with pytest.raises(ValidationError):
        ReflectionDecision(reflection_reason="x", refined_query="")


def test_intent_decision_shopping_has_no_reply():
    decision = IntentDecision(is_shopping_related=True, reply=None)
    assert decision.reply is None


def test_intent_decision_general_has_reply():
    decision = IntentDecision(is_shopping_related=False, reply="Hi! I'm a laptop shopping assistant.")
    assert decision.is_shopping_related is False
    assert decision.reply == "Hi! I'm a laptop shopping assistant."
