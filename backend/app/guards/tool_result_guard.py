REQUIRED_KEYS = ("title", "url")


def filter_valid_results(raw_results: list[dict]) -> tuple[list[dict], int]:
    """Keep only results that carry the minimum required fields.

    Returns (valid_results, discarded_count). Never fabricates missing fields —
    an incomplete result is dropped rather than patched with guessed data.
    """
    valid: list[dict] = []
    discarded = 0

    for item in raw_results:
        if isinstance(item, dict) and all(item.get(key) for key in REQUIRED_KEYS):
            valid.append(item)
        else:
            discarded += 1

    return valid, discarded
