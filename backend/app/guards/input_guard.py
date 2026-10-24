import unicodedata

MAX_QUERY_LENGTH = 500


class InvalidQueryError(ValueError):
    pass


def validate_input(raw_query: str, label: str = "Query") -> str:
    # NFC so Vietnamese diacritics typed as combining marks compare/search like precomposed ones;
    # control characters (other than whitespace) carry no meaning in a query and are dropped.
    query = unicodedata.normalize("NFC", raw_query or "")
    query = "".join(ch for ch in query if ch.isprintable() or ch.isspace()).strip()

    if not query:
        raise InvalidQueryError(f"{label} must not be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(f"{label} must be at most {MAX_QUERY_LENGTH} characters.")

    return query
