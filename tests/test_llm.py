import pytest
from app.schemas import NormalizedLead, LeadCategory
from app.services.llm import parse_ai_json, fallback_result, generate_ai_result

LEAD = NormalizedLead(name="Jane", email="jane@acme.com", message="I want a website")


def test_parse_ai_json_maps_department():
    raw = ('{"intent":"request_quote","category":"web_development","confidence":0.9,'
           '"summary":"wants a site","questions":["How many pages?"]}')
    result = parse_ai_json(raw, LEAD)
    assert result.category == LeadCategory.web_development
    assert result.department == "Web"


def test_parse_ai_json_raises_on_bad_json():
    with pytest.raises(ValueError):
        parse_ai_json("not json", LEAD)


def test_fallback_result_is_needs_clarification():
    result = fallback_result(LEAD)
    assert result.category == LeadCategory.needs_clarification
    assert len(result.questions) >= 3


def test_generate_ai_result_mock_mode_returns_valid_result(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    from app.core.config import get_settings
    get_settings.cache_clear()
    result = generate_ai_result(LEAD)
    assert result.department in {"Web", "Mobile", "AI/Automation", "Consulting", "Other"}
    assert result.questions
