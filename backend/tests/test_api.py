import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

REQUIRES_LIVE_KEYS = (
    not settings.google_api_key or not settings.tavily_api_key or not settings.groq_api_key
)
SKIP_REASON = "Requires real GOOGLE_API_KEY, TAVILY_API_KEY and GROQ_API_KEY in .env"


def test_query_rejects_empty_query():
    with TestClient(app) as client:
        response = client.post("/api/v1/shopping/query", json={"query": "   "})
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "invalid_query"


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_query_off_topic_returns_general_reply():
    with TestClient(app) as client:
        response = client.post("/api/v1/shopping/query", json={"query": "hello there"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "done"
    assert body["data"]["recommendation"] is None
    assert body["data"]["general_reply"]


def test_resume_unknown_thread_returns_404():
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/shopping/resume/{uuid.uuid4()}",
            json={"approved": True, "feedback": None},
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "thread_not_found"


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_query_then_resume_approve_flow():
    with TestClient(app) as client:
        query_response = client.post(
            "/api/v1/shopping/query",
            json={"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"},
        )
        assert query_response.status_code == 200
        query_body = query_response.json()
        assert query_body["status"] == "pending_approval"
        thread_id = query_body["thread_id"]

        resume_response = client.post(
            f"/api/v1/shopping/resume/{thread_id}",
            json={"approved": True, "feedback": None},
        )
        assert resume_response.status_code == 200
        resume_body = resume_response.json()
        assert resume_body["thread_id"] == thread_id
        assert resume_body["status"] == "done"
        assert resume_body["data"]["recommendation"]["product_name"]


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_resume_reject_then_approve_flow():
    with TestClient(app) as client:
        query_response = client.post(
            "/api/v1/shopping/query",
            json={"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"},
        )
        thread_id = query_response.json()["thread_id"]

        reject_response = client.post(
            f"/api/v1/shopping/resume/{thread_id}",
            json={"approved": False, "feedback": "prefer AMD GPU"},
        )
        assert reject_response.status_code == 200
        assert reject_response.json()["status"] == "pending_approval"

        approve_response = client.post(
            f"/api/v1/shopping/resume/{thread_id}",
            json={"approved": True, "feedback": None},
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "done"


@pytest.mark.skipif(REQUIRES_LIVE_KEYS, reason=SKIP_REASON)
def test_resume_on_already_finished_thread_returns_409():
    with TestClient(app) as client:
        query_response = client.post(
            "/api/v1/shopping/query",
            json={"query": "laptop duoi 25 trieu cho lap trinh AI va gaming"},
        )
        thread_id = query_response.json()["thread_id"]
        client.post(
            f"/api/v1/shopping/resume/{thread_id}",
            json={"approved": True, "feedback": None},
        )

        again_response = client.post(
            f"/api/v1/shopping/resume/{thread_id}",
            json={"approved": True, "feedback": None},
        )
    assert again_response.status_code == 409
    assert again_response.json()["error"]["code"] == "thread_already_finished"
