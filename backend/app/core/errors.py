from app.core.llm import ApiKeysExhaustedError, is_provider_unavailable
from app.core.logging import logger


class AppError(Exception):
    """A failure reported to the client: HTTP status, a stable code, and a message written for the user."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def body(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


def to_app_error(exc: Exception, thread_id: str) -> AppError:
    """Classify a failed graph run. Provider outages are expected and logged briefly; anything else gets a traceback."""
    if isinstance(exc, ApiKeysExhaustedError):
        logger.warning("Thread %s stopped: every API key is out of quota", thread_id)
        return AppError(
            503,
            "llm_quota_exhausted",
            "The AI service has reached its usage limit for now. Please try again in a few minutes.",
        )
    if is_provider_unavailable(exc):
        logger.warning("Thread %s stopped: model provider unavailable (%s)", thread_id, type(exc).__name__)
        return AppError(503, "llm_unavailable", "The AI service is busy right now. Please try again in a moment.")

    logger.exception("Graph run failed for thread %s", thread_id, exc_info=exc)
    return AppError(500, "internal_error", "An unexpected error occurred.")
