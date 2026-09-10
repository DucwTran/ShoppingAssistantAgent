MAX_QUERY_LENGTH = 500


class InvalidQueryError(ValueError):
    pass


def validate_input(raw_query: str) -> str:
    query = (raw_query or "").strip()

    if not query:
        raise InvalidQueryError("Query must not be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(f"Query must be at most {MAX_QUERY_LENGTH} characters.")

    return query
