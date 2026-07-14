from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
from app.schemas import InboundForm
from app.core.config import get_settings
from app.services.prefilter import normalize, is_junk
from app.services.llm import generate_ai_result
from app.services.emailer import send_lead_email
from app.services.odoo import log_lead

app = FastAPI(title="AI Lead Automation")

# Health
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


#Entry point
@app.post("/webhook/lead")
async def webhook_lead(form: InboundForm,background: BackgroundTasks,x_webhook_secret: str | None = Header(default=None),
) -> dict:
    settings = get_settings()
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="invalid webhook secret")

    # Normalization of form
    lead = normalize(form)

    # If the message < 3 words.
    if is_junk(lead):
        return {"status": "ignored", "reason": "junk"}
    
    print("-----Lead Info-------")
    print(lead)
    print("---------------------")

    ai = await generate_ai_result(lead)

    print("-----Lead Info generate_ai_result function-------")
    print(lead)
    print("---------------------")

    print("----AI-----")
    print(ai)
    print("-----------")
    
    background.add_task(send_lead_email, lead, ai)
    background.add_task(log_lead, lead, ai)

    return {
        "status": "accepted",
        "department": ai.department,
        "category": ai.category.value,
        "summary": ai.summary,
        "questions": ai.questions,
    }
