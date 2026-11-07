from fastapi.testclient import TestClient

from owasp_rag.api import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_ask_rejects_empty_and_oversized_questions():
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/ask", json={"question": "x" * 2001}).status_code == 422
