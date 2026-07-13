# AI / LLM Logic

## Design goal: one call, minimal tokens

Classification and dynamic question generation are collapsed into **a single
Gemini call** (`app/services/llm.py::generate_ai_result`) instead of two
separate calls. This halves both token usage and API round-trips, keeps the
service comfortably inside Gemini's free-tier rate limits, and avoids the
extra latency and failure surface of a second network call.

Model: `gemini-2.0-flash`, `temperature=0.2` (favors consistent, repeatable
classification over creative variation), `max_output_tokens=1024` (hard cap —
the response can never balloon), `response_mime_type="application/json"`
(forces structured output, no prose to parse around).

## The JSON contract

```json
{
  "intent": "request_quote",
  "category": "web_development",
  "confidence": 0.9,
  "summary": "E-commerce store for ~200 products with card payments",
  "questions": [
    "Which payment gateways do you need?",
    "Do you have product data ready?",
    "Do you need ongoing maintenance?"
  ]
}
```

`department` is **not** requested from the model — it's derived deterministically
in code from `category` via `DEPARTMENT_MAP` (`app/core/config.py`). This keeps
routing reliable and Odoo-mappable; the model is never asked to invent a
free-text department name.

## Category taxonomy

A fixed enum, not free text, so routing can't drift:

| `category` | Department |
|---|---|
| `web_development` | Web |
| `mobile_development` | Mobile |
| `ai_automation` | AI/Automation |
| `consulting` | Consulting |
| `needs_clarification` | Other (Review) |
| `other` | Other |

## Prompt engineering strategy (`app/core/prompts.py`)

- **Role framing** — the model is told it's a lead-qualification assistant
  for a software company, not a general chatbot.
- **Constrained output** — the exact key set and the allowed `category`
  values are spelled out in the instruction, so the model can't invent new
  fields or categories.
- **Few-shot examples** — two worked examples are included: one detailed
  message → confident classification with specific questions, one vague
  message → `needs_clarification` with broad, safe questions. This anchors
  the model's behavior on both ends of the input-quality spectrum.
- **Gap-aware questions** — the prompt explicitly instructs the model to ask
  only for information the customer *hasn't already given*, bounded to 3–6
  questions, so replies stay short and relevant rather than generic.
- **JSON-only, low temperature** — minimizes parsing failures and keeps
  classification stable across repeated similar inputs.

## Parsing logic (`parse_ai_json`)

The raw model response is parsed with `json.loads`, then the `category`
string is coerced through the `LeadCategory` enum — an invalid category value
raises immediately rather than silently accepting garbage. `department` is
looked up from `DEPARTMENT_MAP`, never trusted from the model. Every field
flows through the `AIResult` Pydantic model, which enforces types and the
`0.0–1.0` bound on `confidence`.

## Reliability & fallback chain

| Failure | Handling |
|---|---|
| Gemini rate limit / timeout | Retried up to 3 times with exponential backoff (`tenacity`), then falls through to `fallback_result()`. |
| Malformed / non-JSON response | `parse_ai_json` raises `ValueError`; caught by `generate_ai_result`, which returns `fallback_result()`. |
| Any other Gemini/network error | Caught broadly in `generate_ai_result`; never propagates to the webhook caller. |
| Vague input that *does* parse | The model itself is instructed to return `needs_clarification` with broad questions — this is a model decision, not a code branch. |
| Empty / near-empty input | Never reaches the model — `services/prefilter.py::is_junk` rejects it first (saves tokens, returns `{"status":"ignored"}`). |

`fallback_result()` returns a complete, valid `AIResult` in the
`needs_clarification` category with generic-but-professional questions, so
the customer still receives a coherent email and the lead is still logged —
just flagged for human review — even if Gemini is completely unreachable.
**The flow never hard-fails on an LLM error.**

## Mock mode

`LLM_MODE=mock` (the default) bypasses Gemini entirely and uses a small
keyword-based heuristic (`_mock_result`) that mimics the same category
distribution and returns the same `AIResult` shape. This lets the full
pipeline — webhook → classify → email → Odoo — be developed and tested with
**zero API calls and zero cost**. Switching to `LLM_MODE=live` changes only
which function produces the `AIResult`; every downstream consumer
(`emailer.py`, `odoo.py`, the webhook response) is unaffected.
