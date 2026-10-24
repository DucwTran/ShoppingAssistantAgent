import json
import logging
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.api import health
from app.core import checkpointer, logging as app_logging
from app.core.config import settings
from app.graph.graph import build_graph
from app.main import app
from app.tools import web_search


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpointer, "CHECKPOINT_DB", tmp_path / "checkpoints.sqlite")
    with TestClient(app) as test_client:
        yield test_client


class _Records(logging.Handler):
    """Collects records after the app's context filter has run, as the real handler sees them."""

    def __init__(self):
        super().__init__()
        self.addFilter(app_logging._ContextFilter())
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@pytest.fixture
def records():
    handler = _Records()
    app_logging.logger.addHandler(handler)
    yield handler.records
    app_logging.logger.removeHandler(handler)


# --- configuration --------------------------------------------------------------------------------


def test_production_refuses_to_start_without_required_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpointer, "CHECKPOINT_DB", tmp_path / "checkpoints.sqlite")
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "tavily_api_key", "")
    with pytest.raises(RuntimeError, match="TAVILY_API_KEY"):
        with TestClient(app):
            pass


# --- health ---------------------------------------------------------------------------------------


def test_liveness_needs_nothing_but_the_process(client):
    response = client.get("/health/live")
    assert response.status_code == 200 and response.json() == {"status": "ok"}


def test_readiness_reports_each_dependency(client, monkeypatch):
    monkeypatch.setattr(health, "index_exists", lambda: True)
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"checkpointer": True, "knowledge_index": True}}

    monkeypatch.setattr(health, "index_exists", lambda: False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["knowledge_index"] is False


# --- request id and logs --------------------------------------------------------------------------


def test_request_id_is_returned_and_reused_when_well_formed(client):
    generated = client.get("/health/live").headers["X-Request-ID"]
    assert len(generated) == 32

    assert client.get("/health/live", headers={"X-Request-ID": "proxy-abc.123"}).headers["X-Request-ID"] == "proxy-abc.123"
    replaced = client.get("/health/live", headers={"X-Request-ID": "bad id\n"}).headers["X-Request-ID"]
    assert replaced != "bad id\n" and len(replaced) == 32


def test_every_log_line_of_a_request_carries_its_id(client, fake_pipeline, records):
    response = client.post("/api/v1/shopping/query", json={"query": "laptop gaming dưới 25 triệu"},
                           headers={"X-Request-ID": "req-1"})
    assert response.status_code == 200

    # Node events are logged from LangGraph's worker threads; the id still reaches them
    node_records = [r for r in records if r.fields.get("node") == "recommend"]
    assert node_records and all(r.request_id == "req-1" for r in node_records)
    access = [r for r in records if r.fields.get("event") == "request"]
    assert access[-1].fields["status_code"] == 200 and access[-1].request_id == "req-1"


def test_health_polls_write_no_access_log(client, records):
    client.get("/health/live")
    assert not [r for r in records if r.fields.get("event") == "request"]


def test_json_formatter_writes_one_parseable_object_per_line():
    record = logging.LogRecord("shopping_assistant", logging.WARNING, __file__, 1, "line", None, None)
    record.request_id = "req-1"
    record.fields = {"message": "Research agent failed", "event": "research_agent_failed", "node": "research_agent"}

    entry = json.loads(app_logging._JsonFormatter().format(record))
    assert entry["level"] == "WARNING" and entry["request_id"] == "req-1"
    assert entry["message"] == "Research agent failed" and entry["event"] == "research_agent_failed"


def test_graph_events_outside_a_request_have_no_id(fake_pipeline, records):
    build_graph().invoke({"query": "laptop gaming"}, {"configurable": {"thread_id": str(uuid.uuid4())}})
    assert records and all(r.request_id is None for r in records)


# --- timeouts -------------------------------------------------------------------------------------


def test_a_stalled_web_search_times_out(monkeypatch):
    class _Stalled:
        def invoke(self, payload):
            time.sleep(1)
            return {"results": []}

    monkeypatch.setattr(web_search, "_client", lambda: _Stalled())
    monkeypatch.setattr(settings, "web_search_timeout_seconds", 0.05)
    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        web_search.search_web("laptop")
    assert time.perf_counter() - started < 0.5
