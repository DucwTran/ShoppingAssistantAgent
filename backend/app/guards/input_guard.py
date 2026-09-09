MAX_QUERY_LENGTH = 500

SHOPPING_KEYWORDS = [
    "laptop",
    "may tinh",
    "máy tính",
    "gpu",
    "cpu",
    "ram",
    "vga",
    "gaming",
    "choi game",
    "chơi game",
    "ai",
    "lap trinh",
    "lập trình",
    "budget",
    "ngan sach",
    "ngân sách",
    "trieu",
    "triệu",
    "pin",
    "battery",
    "mua",
    "buy",
    "recommend",
    "goi y",
    "gợi ý",
    "so sanh",
    "so sánh",
    "compare",
]


class InvalidQueryError(ValueError):
    pass


def validate_input(raw_query: str) -> str:
    query = (raw_query or "").strip()

    if not query:
        raise InvalidQueryError("Query must not be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(f"Query must be at most {MAX_QUERY_LENGTH} characters.")

    lowered = query.lower()
    if not any(keyword in lowered for keyword in SHOPPING_KEYWORDS):
        raise InvalidQueryError("Query does not appear to be related to laptop shopping.")

    return query
