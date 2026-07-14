import re
from app.schemas import InboundForm, NormalizedLead

_WS = re.compile(r"\s+")


# For cleaning the Json Format provided by the user using Post
def normalize(form: InboundForm) -> NormalizedLead:
    def clean(value: str | None) -> str | None:
        if value is None:
            return None
        return _WS.sub(" ", value).strip()

    return NormalizedLead(
        name=clean(form.name) or "",
        email=form.email,
        message=clean(form.message) or "",
        subject=clean(form.subject),
        phone=clean(form.phone),
    )


# If the len message is less then 3 words.
def is_junk(lead: NormalizedLead) -> bool:
    stripped = re.sub(r"[^A-Za-z0-9]", "", lead.message)
    return len(stripped) < 3
