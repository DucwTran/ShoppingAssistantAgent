import pytest

from app.core import structured
from app.schemas.evaluation import PurposeJudgement


def _use(monkeypatch, *outcomes) -> list:
    """Script the LLM: each call returns or raises the next outcome; returns the outcomes left."""
    remaining = list(outcomes)

    def generate(schema, messages, thinking_level):
        outcome = remaining.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(structured, "_generate", generate)
    return remaining


def test_returns_valid_generation(monkeypatch):
    good = PurposeJudgement(purpose_fit=0.9, feedback="ok")
    _use(monkeypatch, good)
    assert structured.invoke_structured(PurposeJudgement, [("human", "x")]) == good


def test_empty_generation_is_retried(monkeypatch):
    good = PurposeJudgement(purpose_fit=0.9, feedback="ok")
    remaining = _use(monkeypatch, None, good)
    assert structured.invoke_structured(PurposeJudgement, [("human", "x")]) == good
    assert remaining == []


def test_check_rejection_is_retried_then_raised(monkeypatch):
    _use(monkeypatch, *[PurposeJudgement(purpose_fit=0.1, feedback="")] * 3)

    def reject(result):
        raise ValueError("not acceptable")

    with pytest.raises(ValueError):
        structured.invoke_structured(PurposeJudgement, [("human", "x")], check=reject)


def test_transport_errors_propagate_without_retry(monkeypatch):
    remaining = _use(monkeypatch, ConnectionError("down"), PurposeJudgement(purpose_fit=1, feedback=""))
    with pytest.raises(ConnectionError):
        structured.invoke_structured(PurposeJudgement, [("human", "x")])
    assert len(remaining) == 1
