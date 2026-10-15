import httpx
import pytest
from google.genai.errors import ClientError, ServerError

from app.core import llm
from app.core.config import settings


def _client_error(code: int, message: str = "error") -> ClientError:
    return ClientError(code, {"error": {"code": code, "message": message, "status": "ERROR"}})


def _wrapped(error: ClientError) -> RuntimeError:
    """LangChain raises its own error with the SDK's ClientError as the cause."""
    try:
        raise RuntimeError("Error calling model") from error
    except RuntimeError as wrapped:
        return wrapped


@pytest.fixture(autouse=True)
def _three_keys(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_keys", ["k1", "k2", "k3"])
    monkeypatch.setattr(llm, "_current_key", 0)


def _scripted(outcomes: dict):
    """A call that records the keys it was given and fails or succeeds per key."""
    used = []

    def call(key):
        used.append(key)
        outcome = outcomes[key]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    return call, used


def test_rotates_to_next_key_on_quota_error():
    call, used = _scripted({"k1": _wrapped(_client_error(429)), "k2": "ok"})
    assert llm.with_key_rotation(call) == "ok"
    assert used == ["k1", "k2"]


def test_exhausted_key_is_skipped_by_later_calls():
    llm.with_key_rotation(_scripted({"k1": _wrapped(_client_error(429)), "k2": "ok"})[0])
    call, used = _scripted({"k2": "ok"})
    llm.with_key_rotation(call)
    assert used == ["k2"]


def test_invalid_key_rotates():
    call, used = _scripted({"k1": _client_error(400, "API key not valid"), "k2": "ok"})
    assert llm.with_key_rotation(call) == "ok"


def test_non_key_error_propagates_without_rotation():
    call, used = _scripted({"k1": _client_error(400, "Invalid JSON payload")})
    with pytest.raises(ClientError):
        llm.with_key_rotation(call)
    assert used == ["k1"]


def test_raises_when_every_key_fails():
    error = _client_error(429)
    call, used = _scripted({"k1": error, "k2": error, "k3": error})
    with pytest.raises(llm.ApiKeysExhaustedError):
        llm.with_key_rotation(call)
    assert used == ["k1", "k2", "k3"]


def test_provider_outage_is_recognized_through_wrappers():
    outage = ServerError(503, {"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}})
    assert llm.is_provider_unavailable(_wrapped(outage))
    assert llm.is_provider_unavailable(httpx.ReadTimeout("timed out"))
    assert not llm.is_provider_unavailable(_wrapped(_client_error(400)))


def test_no_keys_configured(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_keys", [])
    with pytest.raises(RuntimeError, match="GEMMA_API_KEY"):
        llm.with_key_rotation(lambda key: key)
