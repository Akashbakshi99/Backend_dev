import json
import xmlrpc.client
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas import NormalizedLead, AIResult
from app.core.config import get_settings

FAILED_LOG = "failed_leads.jsonl"


def build_lead_vals(lead: NormalizedLead, ai: AIResult) -> dict:
    questions = "\n".join(f"- {q}" for q in ai.questions)
    description = (
        f"Routed to: {ai.department}\n"
        f"Intent: {ai.intent} (confidence {ai.confidence:.2f})\n\n"
        f"Original message:\n{lead.message}\n\n"
        f"AI follow-up questions:\n{questions}"
    )
    return {
        "name": ai.summary or f"Lead from {lead.name}",
        "contact_name": lead.name,
        "email_from": lead.email,
        "description": description,
        "type": "lead",
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _create_lead(vals: dict) -> int:
    settings = get_settings()
    common = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(settings.odoo_db, settings.odoo_username, settings.odoo_api_key, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/object")
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
        record_id = _create_lead(vals)
        return str(record_id)
    except Exception:
        with open(FAILED_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(vals) + "\n")
        return "queued"
