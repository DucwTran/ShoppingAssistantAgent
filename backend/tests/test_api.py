import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.core import checkpointer
from app.core.config import settings
from app.core.llm import ApiKeysExhaustedError
from app.main import app

QUERY = "laptop dưới 25 triệu cho lập trình AI và gaming"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(checkpointer, "CHECKPOINT_DB", tmp_path / "checkpoints.sqlite")
    with TestClient(app) as test_client:
        yield test_client


def _sse_frames(body: str) -> list[tuple[str, dict]]:
    frames = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        frames.append((lines["event"], json.loads(lines["data"])))
    return frames


# --- offline ---------------------------------------------------------------------------------------


def test_query_rejects_empty_query(client):
    response = client.post("/api/v1/shopping/query", json={"query": "   "})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_query"


def test_stream_rejects_empty_query_before_streaming(client):
    response = client.post("/api/v1/shopping/query/stream", json={"query": "   "})
    assert response.status_code == 400


def test_resume_unknown_thread_returns_404(client):
    response = client.post(f"/api/v1/shopping/resume/{uuid.uuid4()}", json={"approved": True, "feedback": None})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "thread_not_found"


def test_query_then_approve_flow(client, fake_pipeline):
    body = client.post("/api/v1/shopping/query", json={"query": QUERY}).json()
    assert body["status"] == "pending_approval"
    assert body["data"]["recommendation"]["url"]

    resumed = client.post(f"/api/v1/shopping/resume/{body['thread_id']}", json={"approved": True}).json()
    assert resumed["status"] == "done"

    again = client.post(f"/api/v1/shopping/resume/{body['thread_id']}", json={"approved": True})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "thread_already_finished"


def test_general_chat_returns_reply(client, fake_pipeline):
    fake_pipeline.is_shopping = False
    body = client.post("/api/v1/shopping/query", json={"query": "hello"}).json()
    assert body["status"] == "done"
    assert body["data"]["recommendation"] is None
    assert body["data"]["general_reply"] == "Xin chào!"


def test_rejection_cap_reports_rejected(client, fake_pipeline, monkeypatch):
    monkeypatch.setattr(settings, "max_human_rejections", 1)
    thread_id = client.post("/api/v1/shopping/query", json={"query": QUERY}).json()["thread_id"]
    body = client.post(f"/api/v1/shopping/resume/{thread_id}", json={"approved": False, "feedback": "no"}).json()
    assert body["status"] == "rejected"


def test_query_stream_emits_progress_then_result(client, fake_pipeline):
    response = client.post("/api/v1/shopping/query/stream", json={"query": QUERY})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    frames = _sse_frames(response.text)
    events = [event for event, _ in frames]
    assert events[-1] == "result"
    assert "progress" in events
    progress_nodes = {data["node"] for event, data in frames if event == "progress"}
    assert {"understand", "research_agent", "extract_products", "recommend"} <= progress_nodes

    result = frames[-1][1]
    assert result["status"] == "pending_approval"

    resumed = _sse_frames(
        client.post(f"/api/v1/shopping/resume/{result['thread_id']}/stream", json={"approved": True}).text
    )
    assert resumed[-1][1]["status"] == "done"


def test_query_stream_reports_failure_in_band(client, fake_pipeline):
    fake_pipeline.product_id = 99  # invalid id -> node fails after streaming has started
    event, data = _sse_frames(client.post("/api/v1/shopping/query/stream", json={"query": QUERY}).text)[-1]
    assert event == "error"
    assert data["status"] == 500
    assert data["error"] == {"code": "internal_error", "message": "An unexpected error occurred."}
    assert data["thread_id"]


def test_exhausted_api_keys_return_503_with_user_message(client, fake_pipeline):
    fake_pipeline.failures["RecommendationChoice"] = ApiKeysExhaustedError("all keys failed")
    response = client.post("/api/v1/shopping/query", json={"query": QUERY})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "llm_quota_exhausted"


def test_stream_reports_provider_outage_in_band(client, fake_pipeline):
    fake_pipeline.failures["RecommendationChoice"] = ApiKeysExhaustedError("all keys failed")
    event, data = _sse_frames(client.post("/api/v1/shopping/query/stream", json={"query": QUERY}).text)[-1]
    assert event == "error"
    assert data["status"] == 503
    assert data["error"]["code"] == "llm_quota_exhausted"


def test_retry_continues_a_failed_query_from_the_failed_step(client, fake_pipeline):
    fake_pipeline.failures["PurposeJudgement"] = ApiKeysExhaustedError("all keys failed")  # the last LLM step
    _, error = _sse_frames(client.post("/api/v1/shopping/query/stream", json={"query": QUERY}).text)[-1]

    frames = _sse_frames(client.post(f"/api/v1/shopping/retry/{error['thread_id']}/stream").text)
    assert frames[-1][0] == "result"
    assert frames[-1][1]["status"] == "pending_approval"
    # Only the failed step ran again; the earlier steps were not repeated.
    assert fake_pipeline.calls.count("RecommendationChoice") == 1
    assert fake_pipeline.calls.count("PurposeJudgement") == 2


def test_retry_continues_a_failed_refinement(client, fake_pipeline):
    fake_pipeline.needs_new_products = True
    thread_id = client.post("/api/v1/shopping/query", json={"query": QUERY}).json()["thread_id"]

    fake_pipeline.failures["FeedbackDecision"] = ApiKeysExhaustedError("all keys failed")
    failed = client.post(f"/api/v1/shopping/resume/{thread_id}", json={"approved": False, "feedback": "AMD"})
    assert failed.status_code == 503

    # A failed run takes no new decision; it can only be retried, and the rejection already recorded stands.
    decision = client.post(f"/api/v1/shopping/resume/{thread_id}", json={"approved": True})
    assert decision.status_code == 409
    assert decision.json()["error"]["code"] == "not_awaiting_decision"

    retried = client.post(f"/api/v1/shopping/retry/{thread_id}")
    assert retried.status_code == 200
    assert retried.json()["status"] == "pending_approval"
    assert fake_pipeline.calls.count("FeedbackDecision") == 2


def test_retry_is_refused_when_nothing_failed(client, fake_pipeline):
    thread_id = client.post("/api/v1/shopping/query", json={"query": QUERY}).json()["thread_id"]
    response = client.post(f"/api/v1/shopping/retry/{thread_id}")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "nothing_to_retry"


# --- live ------------------------------------------------------------------------------------------


@pytest.mark.live
def test_live_query_then_resume(client):
    body = client.post("/api/v1/shopping/query", json={"query": QUERY}).json()
    assert body["status"] == "pending_approval"
    recommendation = body["data"]["recommendation"]
    assert recommendation["product_name"] != "N/A" and recommendation["url"]

    resumed = client.post(f"/api/v1/shopping/resume/{body['thread_id']}", json={"approved": True}).json()
    assert resumed["status"] == "done"
