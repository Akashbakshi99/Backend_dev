import json
import logging
import re
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
from app.schemas import NormalizedLead, AIResult, LeadCategory
from app.core.config import get_settings, DEPARTMENT_MAP
from app.core.prompts import build_prompt


def _extract_json_object(raw: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace:
        return brace.group(0)
    return raw


def parse_ai_json(raw: str, lead: NormalizedLead) -> AIResult:
    try:
        data = json.loads(_extract_json_object(raw))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON from model: {exc}") from exc
    category = LeadCategory(data["category"])
    return AIResult(
        intent=str(data.get("intent", "general_inquiry")),
        category=category,
        department=DEPARTMENT_MAP[category],
        confidence=float(data.get("confidence", 0.5)),
        summary=str(data.get("summary", "")),
        questions=[str(q) for q in data.get("questions", [])],
    )


def fallback_result(lead: NormalizedLead) -> AIResult:
    return AIResult(
        intent="general_inquiry",
        category=LeadCategory.needs_clarification,
        department=DEPARTMENT_MAP[LeadCategory.needs_clarification],
        confidence=0.2,
        summary="Automatic classification unavailable; needs human review.",
        questions=[
            "Could you tell us more about the product or service you need?",
            "What problem are you hoping to solve?",
            "What is your rough timeline and budget?",
        ],
    )


def _mock_result(lead: NormalizedLead) -> AIResult:
    text = lead.message.lower()
    if any(w in text for w in ("app", "ios", "android")):
        category = LeadCategory.mobile_development
    elif any(w in text for w in ("ai", "automation", "bot", "llm")):
        category = LeadCategory.ai_automation
    elif any(w in text for w in ("website", "web", "store", "ecommerce", "site")):
        category = LeadCategory.web_development
    elif len(lead.message.split()) <= 6:
        category = LeadCategory.needs_clarification
    else:
        category = LeadCategory.consulting
    return AIResult(
        intent="request_quote",
        category=category,
        department=DEPARTMENT_MAP[category],
        confidence=0.75,
        summary=f"[mock] {lead.message[:80]}",
        questions=[
            "What is your target timeline?",
            "What is your approximate budget range?",
            "Do you have any existing systems we should integrate with?",
        ],
    )


def _is_transient_gemini_error(exc: BaseException) -> bool:
    from google.api_core import exceptions as google_exceptions

    return isinstance(exc, (
        google_exceptions.ResourceExhausted,
        google_exceptions.DeadlineExceeded,
        google_exceptions.ServiceUnavailable,
        google_exceptions.InternalServerError,
        google_exceptions.Aborted,
        TimeoutError,
        ConnectionError,
    ))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception(_is_transient_gemini_error),
    reraise=True,
)
def _call_gemini(prompt: str) -> str:
    import google.generativeai as genai

    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-3.1-flash-lite")
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 1024,
                "response_mime_type": "application/json",
            },
        )
    except Exception:
        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.2, "max_output_tokens": 1024},
        )
    return response.text


def generate_ai_result(lead: NormalizedLead) -> AIResult:
    settings = get_settings()
    if settings.llm_mode == "mock":
        return _mock_result(lead)
    try:
        raw = _call_gemini(build_prompt(lead))
        return parse_ai_json(raw, lead)
    except Exception as exc:
        logging.getLogger(__name__).warning("Gemini call failed, using fallback: %s", exc)
        return fallback_result(lead)
