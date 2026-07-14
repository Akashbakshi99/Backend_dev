from app.schemas import NormalizedLead, AIResult, LeadCategory
from app.services.emailer import build_email, send_lead_email

LEAD = NormalizedLead(name="Jane", email="jane@acme.com", message="I want a website")
AI = AIResult(intent="request_quote", category=LeadCategory.web_development,
              department="Web", confidence=0.9, summary="Wants a website",
              questions=["How many pages?", "What is your budget?"])


def test_build_email_sets_headers_and_from(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "sender@example.com")
    from app.core.config import get_settings
    get_settings.cache_clear()

    msg = build_email(LEAD, AI)
    assert msg["To"] == "jane@acme.com"
    assert msg["From"] == "sender@example.com"
    assert "How many pages?" in msg.get_body(preferencelist=("html",)).get_content()


def test_send_lead_email_mock_mode(monkeypatch):
    monkeypatch.setenv("EMAIL_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert send_lead_email(LEAD, AI) == "mock"
