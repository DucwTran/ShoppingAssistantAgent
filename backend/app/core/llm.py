import threading
from collections.abc import Callable
from functools import lru_cache
from typing import Literal, TypeVar

import httpx
from google.genai.errors import ClientError, ServerError
from langchain.agents.middleware import wrap_model_call
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.core.logging import log_event

T = TypeVar("T")

# Index of the key in use, shared by every request so an exhausted key is skipped from then on
_current_key = 0
_key_lock = threading.Lock()


class ApiKeysExhaustedError(RuntimeError):
    """Every configured API key failed on quota or authorization.

    A RuntimeError, so the graph's RetryPolicy does not retry it: another attempt seconds later would
    fail the same way.
    """


def _exception_chain(exc: BaseException | None):
    # LangChain wraps the SDK's errors, so the original is found by walking the chain of causes.
    while exc is not None:
        yield exc
        exc = exc.__cause__


def _is_key_error(exc: BaseException) -> bool:
    """True when the failure belongs to the API key (quota exhausted, invalid or revoked), so another key can succeed."""
    for cause in _exception_chain(exc):
        if isinstance(cause, ClientError):
            return cause.code in (401, 403, 429) or (cause.code == 400 and "API key" in str(cause))
    return False


def is_provider_unavailable(exc: BaseException) -> bool:
    """True when the model provider is overloaded, failing (5xx) or did not answer in time."""
    return any(isinstance(cause, (ServerError, httpx.TimeoutException, TimeoutError)) for cause in _exception_chain(exc))


def with_key_rotation(call: Callable[[str], T]) -> T:
    """Run `call` with the current API key; on a key-level failure switch to the next key and try again.

    Each key is tried at most once per call; when all of them fail, ApiKeysExhaustedError is raised.
    Any other error (bad request, 5xx, timeout) propagates unchanged, so the graph node's RetryPolicy
    handles transient failures.
    """
    global _current_key
    keys = settings.gemini_api_keys
    if not keys:
        raise RuntimeError("No Gemini API key configured: set GEMMA_API_KEY_1, GEMMA_API_KEY_2, ... in .env")

    last_error: Exception | None = None
    for _ in range(len(keys)):
        index = _current_key % len(keys)
        try:
            return call(keys[index])
        except Exception as exc:
            if not _is_key_error(exc):
                raise
            last_error = exc
            with _key_lock:
                if _current_key % len(keys) == index:  # another request may have rotated already
                    _current_key = index + 1
            log_event(node="llm", event="api_key_rotated", status="warning",
                      failed_key=index + 1, next_key=(index + 1) % len(keys) + 1, error=str(exc)[:200])
    raise ApiKeysExhaustedError(f"All {len(keys)} Gemini API keys failed; last error: {last_error}") from last_error


ThinkingLevel = Literal["minimal", "low", "medium", "high"]


@lru_cache(maxsize=None)
def chat_model(api_key: str, thinking_level: ThinkingLevel | None = None) -> ChatGoogleGenerativeAI:
    """`thinking_level` None keeps the model's default; lower it for calls that copy rather than reason."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=api_key,
        timeout=settings.llm_timeout_seconds,
        # 1 = a single attempt (0 means "SDK default"): a key-level failure should rotate at once,
        # not back off and retry on the same exhausted key
        max_retries=1,
        thinking_level=thinking_level,
    )


@wrap_model_call
def key_rotation_middleware(request, handler):
    """Agent middleware: every model call inside the agent loop goes through the key rotation."""
    return with_key_rotation(lambda key: handler(request.override(model=chat_model(key))))
