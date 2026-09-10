import pytest

from app.guards.input_guard import InvalidQueryError, validate_input
from app.guards.tool_argument_guard import ToolArgumentError, call_tool
from app.guards.tool_result_guard import filter_valid_results
from app.tools.registry import TOOLS_BY_NAME


def test_input_guard_rejects_empty():
    with pytest.raises(InvalidQueryError):
        validate_input("   ")


def test_input_guard_accepts_off_topic_text():
    assert validate_input("hom nay thoi tiet the nao?") == "hom nay thoi tiet the nao?"


def test_input_guard_accepts_relevant_query():
    assert validate_input("  laptop gaming duoi 20 trieu  ") == "laptop gaming duoi 20 trieu"


def test_tool_argument_guard_rejects_invalid_args():
    tool = TOOLS_BY_NAME["web_search"]
    with pytest.raises(ToolArgumentError):
        call_tool(tool, query="laptop", max_results=-1)


def test_tool_result_guard_filters_incomplete_results():
    raw = [
        {"title": "Laptop A", "url": "http://a.com", "content": "x"},
        {"title": "Laptop B"},
        {"url": "http://c.com"},
        "not-a-dict",
    ]
    valid, discarded = filter_valid_results(raw)
    assert len(valid) == 1
    assert discarded == 3
