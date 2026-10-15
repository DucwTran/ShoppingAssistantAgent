from app.graph.nodes.metadata import language_name, metadata_node


def test_detects_vietnamese():
    assert metadata_node({"query": "laptop dưới 25 triệu cho lập trình AI và gaming"})["language"] == "vi"


def test_detects_english():
    assert metadata_node({"query": "best laptop under 1000 dollars for gaming"})["language"] == "en"


def test_language_name_defaults_to_vietnamese():
    assert language_name("en") == "English"
    assert language_name(None) == "Vietnamese"
