# AI-Driven Lead Management Automation — Design Spec

**Date:** 2026-07-13
**Context:** Technical assessment for an AI Engineer position.
**Author:** Assessment candidate

---

## 1. Problem & Objective

The company manages inbound business leads manually: a prospect submits a WordPress
contact form → a notification email lands in a general inbox → the Leads Department
manually reads it, logs it into Odoo CRM, and routes it to the right internal team.

**Goal:** automate this workflow end-to-end **up to (but not including) quotation
generation**, eliminating manual handling at the initial customer touchpoints.

On form submission the system must:

1. **Instant, contextual engagement** — immediately email the prospect a professional
   acknowledgement of their *specific inquiry type*, attach the **Company Profile PDF**,
   and engage them with a **dynamic questionnaire**.
2. **Intelligent requirement gathering** — read what the customer wrote and generate a
   specific, highly relevant set of follow-up questions targeting only the missing
   requirements needed for a quote.
3. **Internal automation & smart routing** — capture the lead, categorize it by
   type/intent, log it into **Odoo CRM**, and route it to the correct department with no
   human intervention.

---

## 2. Scope

**In scope**
- Receiving a WordPress-form-shaped payload via a webhook (mocked payload; one flag to go live).
- AI classification (intent + category + department + confidence + summary).
- AI dynamic question generation (gap-aware, tailored to the customer's message).
- Sending a contextual reply email **with the Company Profile PDF attached** and the
  questions embedded in the email body (reply-to-answer).
- Logging the lead into Odoo CRM and routing it to the mapped department.
- Reliability handling: validation, retries, rate-limit backoff, fallbacks, dead-letter.
- Deliverables: runnable repo, architecture README, AI logic doc, walkthrough outline.

**Out of scope (explicitly)**
- Quotation / invoice generation (the brief stops right before this).
- The **return loop** — capturing the customer's answers to the questionnaire. The PoC is
  **outbound only** (send + log). Noted as the natural next stage.
- A hosted interactive web questionnaire (questions are delivered **in the email**).
- A live WordPress installation (a mock CF7-shaped payload fully satisfies the brief).

---

## 3. Tech Stack & Rationale

| Concern | Choice | Why |
|---|---|---|
| Service / orchestration | **Python + FastAPI** (Dockerized) | Native LLM ecosystem; showcases clean code + system design; the FastAPI service *is* the automation layer. |
| LLM | **Google Gemini** (free tier, Flash model) behind a provider-agnostic wrapper | Genuinely free tier; fast; swap-in-one-line abstraction keeps us vendor-neutral. |
| CRM | **Odoo Online** (One-App-Free CRM), XML-RPC external API | Free indefinitely; real integration; full external API. |
| Email | **Gmail SMTP** (app password) | Zero cost, works immediately, supports attachments. |
| Form source | **Mocked WordPress webhook** (Contact Form 7-shaped JSON) | Mock payload satisfies the brief; one config flag switches to live. |
| Packaging | **Docker + docker-compose** | `docker compose up` reproducibility. |

**Token-cost minimization (explicit design goal):**
- **A single Gemini call** returns classification **and** questions in one JSON object
  (not two calls) — halves tokens and API calls, and keeps within free-tier rate limits.
- **Gemini Flash**, low `temperature` for stable classification, capped `max_output_tokens`.
- Compact prompt: tight instructions + 2–3 few-shot examples, JSON-only output.
- A cheap **code pre-filter** rejects empty/gibberish input *before* any LLM call.

**Security (the brief asks to orchestrate "securely"):**
- **Webhook authentication** — a shared-secret header / signature check on `/webhook/lead`
  so arbitrary posters cannot inject leads.
- Secrets only from `.env` (never committed); `.env.example` documents every key.
- Pydantic validation on all inbound data.

**Scalability narrative (for the README):**
- Stateless service → scales horizontally behind a load balancer.
- Slow external work (email, Odoo) runs in FastAPI `BackgroundTasks` so the webhook
  responds fast; the same seams allow swapping in a real queue (Celery/RQ/SQS) later.

---

## 4. Architecture & End-to-End Flow

```
WordPress form (mock/live)
        │  POST /webhook/lead   (raw form payload + auth secret)
        ▼
┌─────────────────────────────────────────────┐
│              FastAPI service                 │
│  1. Authenticate webhook (shared secret)     │
│  2. Validate & normalize   (Pydantic)        │
│  3. Pre-filter junk        (code, no tokens) │
│  4. AI call (Gemini → one JSON):             │
│        intent, category, department,         │
│        confidence, summary, questions[]      │
│  5. Send email + PDF       (Gmail SMTP)      │  ── BackgroundTasks
│  6. Log & route lead       (Odoo XML-RPC)    │  ── BackgroundTasks
│  7. Return 200 + trace_id                    │
└─────────────────────────────────────────────┘
```

Steps 4 = the AI brain; 5–6 = the actuators. **The customer email and the CRM log are
decoupled** — one failing never blocks the other. Each step is an isolated module with a
clean interface, independently testable and mockable.

---

## 5. Module Layout

```
app/
├─ main.py            FastAPI app + /webhook/lead + /health
├─ schemas.py         Pydantic: InboundForm, NormalizedLead, AIResult
├─ core/
│  ├─ config.py       env settings + MOCK/LIVE flags per integration
│  └─ prompts.py      the single combined prompt + few-shot examples
├─ services/
│  ├─ llm.py          provider-agnostic client (Gemini impl) → AIResult
│  ├─ emailer.py      Gmail SMTP, HTML template + PDF attach
│  └─ odoo.py         XML-RPC: create crm.lead, tag + route to dept
├─ mocks/             sample CF7 payloads (vague + detailed), fake adapters
└─ assets/Company_Profile.pdf   (generated sample; replaceable)
tests/                pytest: unit per service + one full-flow integration test
Dockerfile · docker-compose.yml · .env.example · README.md · AI_LOGIC.md
```

---

## 6. AI Logic

**One call, one JSON contract:**

```json
{
  "intent": "request_quote",
  "category": "web_development",
  "department": "Sales - Web Team",
  "confidence": 0.86,
  "summary": "Prospect wants an e-commerce site with payment integration",
  "questions": [
    "Roughly how many products will the store carry?",
    "Which payment gateways do you need (Stripe, PayPal, local)?",
    "Do you have branding/design assets, or need those too?"
  ]
}
```

- **Classification** selects `category` from a **fixed enum**, each mapped
  deterministically to a `department` — so routing is Odoo-mappable, not free-text.
  Placeholder taxonomy (editable in one config file):
  **Web · Mobile · AI/Automation · Consulting · Other**.
- **Question generation** is instructed to ask **only for the gaps** — read what the
  customer already provided and request just the missing technical/business requirements
  needed for a quote. Bounded to ~3–6 questions.
- **Vague / low-confidence input** → model returns category `needs_clarification` with
  safe, broad questions; the Odoo lead is tagged `review-needed`.
- **Prompt strategy** (documented in `AI_LOGIC.md`): role + task framing, the enum,
  2–3 few-shot examples (detailed and vague), strict JSON-only output instruction,
  low temperature, capped output tokens.

---

## 7. Error Handling & Reliability

| Failure | Handling |
|---|---|
| Vague / empty input | Code pre-filter drops true junk; thin-but-real → `needs_clarification` + broad questions, lead tagged `review-needed`. |
| Gemini 429 / timeout | Exponential backoff (`tenacity`, ~3 tries); then **fallback template** email + default questions; lead still logged + flagged. Flow never hard-fails. |
| Malformed LLM JSON | Strict Pydantic parse; one re-ask ("valid JSON only"); then fallback. |
| Odoo down / auth error | Retry; then queue lead to `failed_leads.jsonl` for replay; customer email still sent. |
| Email send failure | Retry; dead-letter log; Odoo lead tagged `email-failed`. |
| Duplicate submissions | Optional idempotency key (email + timestamp hash) to avoid double-logging. |

- **Structured logging** with a per-request `trace_id` so the walkthrough can follow one
  lead through the whole pipeline.
- **Principle:** customer-facing email and CRM log are decoupled; neither blocks the other.

---

## 8. Testing & Deliverables

**Testing**
- Unit tests per service (LLM JSON parsing, email compose, Odoo payload) with externals mocked.
- One integration test running the full pipeline against mocks, asserting: correct
  classification, questions generated, email built with PDF, Odoo `create` called with
  right fields.
- Two fixture payloads — one **detailed**, one deliberately **vague** — to demonstrate
  edge-case handling.

**Deliverables (mapped to the brief)**
- **README.md** — architecture, "why this stack," security & scalability narrative, setup.
- **AI_LOGIC.md** — prompt engineering strategy, parsing logic, fallback/agentic flow.
- **Runnable repo** — `docker compose up`, `.env.example`, sample Company Profile PDF.
- **Walkthrough outline** — scripted 3–5 min Loom covering setup, a live run, and the two
  edge cases (vague input, simulated API failure).

---

## 9. Requirements Traceability

Every brief requirement maps to a design element:

- Instant contextual reply → email referencing detected `category` + `summary`.
- Company Profile PDF → generated sample attached by `emailer.py`.
- Dynamic questionnaire → AI `questions[]` embedded in email.
- Intelligent requirement gathering → gap-aware single Gemini call.
- Capture + categorize by type/intent → `intent` + `category`.
- Log into Odoo CRM → `odoo.py` creates `crm.lead`.
- Route to correct department, no human intervention → enum → department mapping.
- Stops before quotation → flow ends after engage + log.
- Secure & scalable → webhook auth, `.env` secrets, stateless + BackgroundTasks.
- PoC / AI docs / walkthrough → README, AI_LOGIC.md, Loom outline.
