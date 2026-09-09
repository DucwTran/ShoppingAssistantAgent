from datetime import datetime

from app.graph.nodes.metadata import metadata_node


def test_detects_vietnamese():
    result = metadata_node({"query": "laptop dưới 25 triệu cho lập trình AI và gaming"})
    assert result["language"] == "vi"
    datetime.fromisoformat(result["detected_at"])


def test_detects_english():
    result = metadata_node({"query": "best laptop under 1000 dollars for gaming"})
    assert result["language"] == "en"


def test_detected_at_is_utc_iso_format():
    result = metadata_node({"query": "laptop gaming"})
    parsed = datetime.fromisoformat(result["detected_at"])
    assert parsed.tzinfo is not None
