from app.schemas import NormalizedLead

_CATEGORIES = (
    "web_development, mobile_development, ai_automation, consulting, "
    "needs_clarification, other"
)

_EXAMPLES = """
Example 1:
Message: "We need an online store to sell 200 products with card payments."
Output: {"intent":"request_quote","category":"web_development","confidence":0.9,
"summary":"E-commerce store for ~200 products with card payments",
"questions":["Which payment gateways do you need?","Do you have product data ready?","Do you need ongoing maintenance?"]}

Example 2:
Message: "Hi, I have an idea and want to talk."
Output: {"intent":"general_inquiry","category":"needs_clarification","confidence":0.3,
"summary":"Vague inquiry, requirements unknown",
"questions":["What product or service are you interested in?","What problem are you trying to solve?","What is your rough timeline and budget?"]}
""".strip()


def build_prompt(lead: NormalizedLead) -> str:
    return f"""You are a lead-qualification assistant for a software company.
Read the customer's inquiry and return ONLY a JSON object with keys:
intent (string), category (one of: {_CATEGORIES}), confidence (0..1 float),
summary (one sentence), questions (3 to 6 short strings asking ONLY for the
missing information needed to prepare a quote).
Pick needs_clarification when the message is too vague to classify.

{_EXAMPLES}

Customer name: {lead.name}
Customer message: "{lead.message}"
Return the JSON now:"""
