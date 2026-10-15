import pytest
from pydantic import ValidationError

from app.guards.input_guard import InvalidQueryError, validate_input
from app.guards.tool_result_guard import filter_valid_results
from app.tools.agent_tools import web_search


def test_input_guard_rejects_empty():
    with pytest.raises(InvalidQueryError):
        validate_input("   ")


def test_input_guard_accepts_off_topic_text():
    assert validate_input("hom nay thoi tiet the nao?") == "hom nay thoi tiet the nao?"


def test_input_guard_accepts_relevant_query():
    assert validate_input("  laptop gaming duoi 20 trieu  ") == "laptop gaming duoi 20 trieu"


def test_agent_tool_rejects_invalid_args():
    # args_schema is validated before the tool body runs, so no search is made
    with pytest.raises(ValidationError):
        web_search.invoke({"query": "laptop", "max_results": -1})


def test_tool_result_guard_filters_incomplete_results():
    raw = [
        {"title": "Laptop A", "url": "http://a.com", "content": "x"},
        {"title": "Laptop B"},
        {"url": "http://c.com"},
        "not-a-dict",
    ]
    assert filter_valid_results(raw) == [raw[0]]
