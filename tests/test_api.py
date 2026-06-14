"""Tests that do not require an API key."""

from fastapi.testclient import TestClient

from app.main import app
from app.rag import RagEngine

client = TestClient(app)


def test_health_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ask_requires_question() -> None:
    assert client.post("/ask", json={}).status_code == 422


def test_ask_empty_question_rejected() -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422


def test_chunking_overlaps_and_covers() -> None:
    text = " ".join(str(number) for number in range(400))
    chunks = RagEngine._chunk(text)
    assert len(chunks) > 1
    joined = " ".join(chunks).split()
    assert "0" in joined and "399" in joined
