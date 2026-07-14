import asyncio
import json
import xmlrpc.client
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas import NormalizedLead, AIResult
from app.core.config import get_settings
FAILED_LOG = "failed_leads.jsonl"

# Cache the authenticated Odoo uid so we don't call authenticate() on every lead.
_UID_CACHE: dict[tuple, int] = {}

#Auth
def _authenticate(settings) -> int:
    key = (settings.odoo_url, settings.odoo_db, settings.odoo_username, settings.odoo_api_key)
    uid = _UID_CACHE.get(key)
    if uid:
        return uid
    common = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/common")
    uid = common.authenticate(settings.odoo_db, settings.odoo_username, settings.odoo_api_key, {})
    if not uid:
        raise RuntimeError("Odoo authentication failed")
    _UID_CACHE[key] = uid
    return uid


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


def _find_or_create_partner(models, db: str, uid: int, api_key: str, vals: dict) -> int:
    """Find a contact (res.partner) by email, or create one, so the lead's
    'Contact' field (partner_id) is linked instead of empty."""
    email = vals.get("email_from")
    ids = models.execute_kw(
        db, uid, api_key,
        "res.partner", "search", [[["email", "=", email]]], {"limit": 1},
    ) if email else []
    if ids:
        return ids[0]
    return models.execute_kw(
        db, uid, api_key,
        "res.partner", "create",
        [{"name": vals.get("contact_name") or email, "email": email, "phone": vals.get("phone")}],
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _create_lead(vals: dict, department: str) -> int:
    settings = get_settings()
    uid = _authenticate(settings)  # cached after the first lead -- no re-login
    models = xmlrpc.client.ServerProxy(f"{settings.odoo_url}/xmlrpc/2/object")
    partner_id = _find_or_create_partner(models, settings.odoo_db, uid, settings.odoo_api_key, vals)
    vals = {**vals, "partner_id": partner_id}
    team_id = _find_team_id(models, settings.odoo_db, uid, settings.odoo_api_key, department)
    if team_id:
        vals = {**vals, "team_id": team_id}
    return models.execute_kw(
        settings.odoo_db, uid, settings.odoo_api_key,
        "crm.lead", "create", [vals],
    )


async def log_lead(lead: NormalizedLead, ai: AIResult) -> str:
    settings = get_settings()
    vals = build_lead_vals(lead, ai)
    print(f"odoo.py : vals - {vals}")
    if settings.odoo_mode == "mock":# overide into live
        return f"mock-{ai.category.value}"
    try:
        # thread to keep the event loop free.
        record_id = await asyncio.to_thread(_create_lead, vals, ai.department)
        print(f"record id - {record_id}")
        return str(record_id)
    except Exception:
        with open(FAILED_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(vals) + "\n")
        return "queued"

