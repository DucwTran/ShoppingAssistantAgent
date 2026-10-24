from app.graph.nodes.input_validation import input_validation_node
from app.prompts.language import language_name


def test_detects_vietnamese():
    assert input_validation_node({"query": "laptop dưới 25 triệu cho lập trình AI và gaming"})["language"] == "vi"


def test_detects_english():
    assert input_validation_node({"query": "best laptop under 1000 dollars for gaming"})["language"] == "en"


def test_language_name_defaults_to_vietnamese():
    assert language_name("en") == "English"
    assert language_name(None) == "Vietnamese"
