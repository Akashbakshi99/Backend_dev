from app.schemas import NormalizedLead, AIResult, LeadCategory
from app.services.odoo import build_lead_vals, log_lead, _priority_from_confidence

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


def test_build_lead_vals_maps_priority_from_confidence():
    assert build_lead_vals(LEAD, AI)["priority"] == "3"  # confidence 0.9 -> Very High
    vague = AIResult(intent="general_inquiry", category=LeadCategory.needs_clarification,
                     department="Other", confidence=0.2, summary="Vague", questions=["q"])
    assert build_lead_vals(LEAD, vague)["priority"] == "0"  # low confidence -> Low


def test_build_lead_vals_includes_phone_only_when_present():
    assert "phone" not in build_lead_vals(LEAD, AI)  # LEAD has no phone
    with_phone = NormalizedLead(name="Jane", email="jane@acme.com",
                                message="I want a website", phone="+1 555 0100")
    assert build_lead_vals(with_phone, AI)["phone"] == "+1 555 0100"


def test_priority_from_confidence_boundaries():
    assert _priority_from_confidence(0.8) == "3"
    assert _priority_from_confidence(0.6) == "2"
    assert _priority_from_confidence(0.4) == "1"
    assert _priority_from_confidence(0.39) == "0"


def test_log_lead_mock_mode(monkeypatch):
    monkeypatch.setenv("ODOO_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    assert log_lead(LEAD, AI) == "mock-web_development"
