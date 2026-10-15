import py3langid as langid

from app.core.events import emit
from app.graph.state import ShoppingState

# Restrict to the app's practical domain (Vietnamese assistant, English fallback)
# so short/ambiguous queries don't get misclassified as an unrelated language.
langid.set_languages(["vi", "en"])

_LANGUAGE_NAMES = {"vi": "Vietnamese", "en": "English"}


def language_name(code: str | None) -> str:
    """Human-readable language name for prompts; Vietnamese when unknown, the app's primary audience."""
    return _LANGUAGE_NAMES.get(code or "", "Vietnamese")


def metadata_node(state: ShoppingState) -> dict:
    language, _score = langid.classify(state["query"])
    emit("metadata_detected", "Language detected", node="metadata", language=language)
    return {"language": language}
