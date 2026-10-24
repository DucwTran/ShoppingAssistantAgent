# Languages the assistant answers in; also the only ones language detection chooses between
LANGUAGE_NAMES = {"vi": "Vietnamese", "en": "English"}


def language_name(code: str | None) -> str:
    """Human-readable language name for prompts; Vietnamese when unknown, the app's primary audience."""
    return LANGUAGE_NAMES.get(code or "", "Vietnamese")
