from datetime import datetime, timezone

import py3langid as langid

from app.core.events import emit
from app.graph.state import ShoppingState

# Restrict to the app's practical domain (Vietnamese assistant, English fallback)
# so short/ambiguous queries don't get misclassified as an unrelated language.
langid.set_languages(["vi", "en"])


def metadata_node(state: ShoppingState) -> dict:
    language, _score = langid.classify(state["query"])
    detected_at = datetime.now(timezone.utc).isoformat()

    emit("metadata_detected", "Language and timestamp detected", node="metadata", language=language)

    return {"language": language, "detected_at": detected_at}
