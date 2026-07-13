from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from app.schemas import InboundForm
from app.core.config import get_settings
from app.services.prefilter import normalize, is_junk
from app.services.llm import generate_ai_result
from app.services.emailer import send_lead_email
from app.services.odoo import log_lead

app = FastAPI(title="AI Lead Automation")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook/lead")
def webhook_lead(
    form: InboundForm,
    background: BackgroundTasks,
    x_webhook_secret: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    lead = normalize(form)
    if is_junk(lead):
        return {"status": "ignored", "reason": "junk"}

    ai = generate_ai_result(lead)
    background.add_task(send_lead_email, lead, ai)
    background.add_task(log_lead, lead, ai)

    return {
        "status": "accepted",
        "department": ai.department,
        "category": ai.category.value,
        "summary": ai.summary,
        "questions": ai.questions,
    }
