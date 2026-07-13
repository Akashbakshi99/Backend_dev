import pytest
from fastapi.testclient import TestClient
from app.mocks.payloads import DETAILED_PAYLOAD, VAGUE_PAYLOAD


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("EMAIL_MODE", "mock")
    monkeypatch.setenv("ODOO_MODE", "mock")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    from app.core.config import get_settings
    get_settings.cache_clear()
    from app.main import app
    return TestClient(app)


def test_webhook_rejects_bad_secret(client):
    resp = client.post("/webhook/lead", json=DETAILED_PAYLOAD, headers={"X-Webhook-Secret": "wrong"})
    assert resp.status_code == 401


def test_webhook_accepts_detailed_lead(client):
    resp = client.post("/webhook/lead", json=DETAILED_PAYLOAD, headers={"X-Webhook-Secret": "test-secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["category"] == "web_development"
    assert body["questions"]


def test_webhook_ignores_junk(client):
    resp = client.post("/webhook/lead", json={"name": "x", "email": "x@y.com", "message": "  "},
                       headers={"X-Webhook-Secret": "test-secret"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ignored"


def test_webhook_handles_vague_lead(client):
    resp = client.post("/webhook/lead", json=VAGUE_PAYLOAD, headers={"X-Webhook-Secret": "test-secret"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["category"] == "needs_clarification"
    assert body["department"] == "Other (Review)"
