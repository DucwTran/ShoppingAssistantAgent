REQUIRED_KEYS = ("title", "url")


def filter_valid_results(raw_results: list[dict]) -> list[dict]:
    """Keep only results that carry the minimum required fields.

    Never fabricates missing fields - an incomplete result is dropped rather than patched with guessed data.
    """
    return [item for item in raw_results if isinstance(item, dict) and all(item.get(key) for key in REQUIRED_KEYS)]
