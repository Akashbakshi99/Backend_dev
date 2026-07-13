from app.schemas import LeadCategory, InboundForm, NormalizedLead, AIResult
from app.core.config import DEPARTMENT_MAP


def test_inbound_form_parses_cf7_payload():
    form = InboundForm(name="Jane", email="jane@acme.com", message="I need a website")
    assert form.name == "Jane"
    assert form.subject is None


def test_ai_result_requires_valid_category():
    result = AIResult(
        intent="request_quote",
        category=LeadCategory.web_development,
        department="Web",
        confidence=0.9,
        summary="Wants a website",
        questions=["How many pages?"],
    )
    assert result.category == LeadCategory.web_development


def test_department_map_covers_every_category():
    for category in LeadCategory:
        assert category in DEPARTMENT_MAP
