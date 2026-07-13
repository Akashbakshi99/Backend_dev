from app.schemas import NormalizedLead, AIResult, LeadCategory
from app.services.odoo import build_lead_vals, log_lead

LEAD = NormalizedLead(name="Jane", email="jane@acme.com", message="I want a website")
AI = AIResult(intent="request_quote", category=LeadCategory.web_development,
              department="Web", confidence=0.9, summary="Wants a website",
              questions=["How many pages?"])


def test_build_lead_vals_includes_routing_and_contact():
    vals = build_lead_vals(LEAD, AI)
    assert vals["contact_name"] == "Jane"
    assert vals["email_from"] == "jane@acme.com"
    assert "Web" in vals["description"]
    assert vals["name"]


def test_log_lead_mock_mode(monkeypatch):
    monkeypatch.setenv("ODOO_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert log_lead(LEAD, AI) == "mock-web_development"
