import json
import xmlrpc.client
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas import NormalizedLead, AIResult
from app.core.config import get_settings

FAILED_LOG = "failed_leads.jsonl"


def _priority_from_confidence(confidence: float) -> str:
    """Map the AI's classification confidence to an Odoo crm.lead priority
    (0 Low .. 3 Very High). Uses the confidence already returned by the single
    Gemini call -- no extra API call or tokens."""
    if confidence >= 0.8:
        return "3"
    if confidence >= 0.6:
        return "2"
    if confidence >= 0.4:
        return "1"
    return "0"


def build_lead_vals(lead: NormalizedLead, ai: AIResult) -> dict:
    questions = "\n".join(f"- {q}" for q in ai.questions)
    description = (
        f"Routed to: {ai.department}\n"
        f"Intent: {ai.intent} (confidence {ai.confidence:.2f})\n\n"
        f"Original message:\n{lead.message}\n\n"
        f"AI follow-up questions:\n{questions}"
    )
    vals = {
        "name": ai.summary or f"Lead from {lead.name}",
        "contact_name": lead.name,
        "email_from": lead.email,
        "description": description,
        "type": "lead",
        "priority": _priority_from_confidence(ai.confidence),
    }
    if lead.phone:
        vals["phone"] = lead.phone
    return vals


def _find_team_id(models, db: str, uid: int, api_key: str, department: str) -> int | None:
    ids = models.execute_kw(
        db, uid, api_key,
        "crm.team", "search", [[["name", "=", department]]], {"limit": 1},
    )
    return ids[0] if ids else None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _create_lead(vals: dict, department: str) -> int:
    settings = get_settings()
    common = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(settings.odoo_db, settings.odoo_username, settings.odoo_api_key, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/object")
    team_id = _find_team_id(models, settings.odoo_db, uid, settings.odoo_api_key, department)
    if team_id:
        vals = {**vals, "team_id": team_id}
    return models.execute_kw(
        settings.odoo_db, uid, settings.odoo_api_key,
        "crm.lead", "create", [vals],
    )


def log_lead(lead: NormalizedLead, ai: AIResult) -> str:
    settings = get_settings()
    vals = build_lead_vals(lead, ai)
    if settings.odoo_mode == "mock":
        return f"mock-{ai.category.value}"
    try:
        record_id = _create_lead(vals, ai.department)
        return str(record_id)
    except Exception:
        with open(FAILED_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(vals) + "\n")
        return "queued"
