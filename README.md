# AI-Driven Lead Management Automation

A FastAPI service that automates inbound lead handling — from a WordPress form
submission up to (but not including) quotation generation — using Google Gemini
for classification and dynamic question generation, Gmail for the instant reply,
and Odoo CRM for logging and department routing.

## What it does

On `POST /webhook/lead` (a WordPress-form-shaped payload):

1. Authenticates the request (shared secret).
2. Validates and normalizes the form data.
3. Pre-filters junk/empty submissions (no API call spent on garbage).
4. Sends the customer's message to Gemini in **one** call, which returns:
   - `intent`, `category` (fixed enum), `confidence`, `summary`
   - 3–6 tailored follow-up questions asking only for what's missing to quote
5. Emails the prospect a contextual reply — referencing their inquiry,
   attaching the **Company Profile PDF**, and embedding the AI-generated
   questions — sent from `akashbakshi.ai@gmail.com`.
6. Logs the lead into **Odoo CRM** (`crm.lead`) with routing notes for the
   mapped department.
7. Steps 5–6 run as decoupled background tasks — the customer email never
   waits on Odoo, and vice versa.

## Why this stack

| Concern | Choice | Why |
|---|---|---|
| Service | **Python + FastAPI** | Native LLM ecosystem, fast to build, clean structure for review. |
| LLM | **Google Gemini** (`gemini-2.0-flash`, free tier) | Zero cost, provider-agnostic wrapper so it can be swapped in one place. |
| CRM | **Odoo Online**, XML-RPC external API | Free (One-App-Free), real integration via Odoo's official API. |
| Email | **Gmail SMTP** (app password) | Zero cost, supports attachments, works immediately. |
| Form source | **Mocked WordPress webhook** | The assignment explicitly permits a mock form payload; the webhook contract is the same either way. |
| Packaging | **Docker + docker-compose** | `docker compose up` reproducibility. |

**Token-cost minimization:** classification and question generation happen in
a **single Gemini call** (not two), on the cheapest model, with a low
temperature and a capped `max_output_tokens`, so a full demo run costs a
fraction of a cent — and development/testing runs entirely in `mock` mode
(zero API calls).

## Security

- `POST /webhook/lead` requires a matching `X-Webhook-Secret` header —
  requests without it get `401`. Set `WEBHOOK_SECRET` in `.env`.
- All secrets (Gemini key, Gmail app password, Odoo API key) load from
  `.env`, which is git-ignored. `.env.example` documents every key.
- Inbound data is validated with Pydantic before anything touches an
  external service.

## Scalability

The service is **stateless** — it can run behind a load balancer with any
number of replicas. Slow external calls (email, Odoo) run in FastAPI
`BackgroundTasks` so the webhook responds immediately; the same seams
(`services/emailer.py`, `services/odoo.py`) can be pointed at a real task
queue (Celery/RQ/SQS) later without changing the calling code.

## Setup

```bash
cp .env.example .env
# fill in GEMINI_API_KEY, GMAIL_APP_PASSWORD, ODOO_URL/ODOO_DB/ODOO_API_KEY

# Option A: Docker
docker compose up --build

# Option B: local venv
pip install -r requirements.txt
python scripts/make_pdf.py       # generates app/assets/Company_Profile.pdf
uvicorn app.main:app --reload
```

Run the tests (fully offline, zero API calls — all three modes default to `mock`):

```bash
pytest -v
```

## Trying it

```bash
curl -X POST http://127.0.0.1:8000/webhook/lead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <your WEBHOOK_SECRET>" \
  -d '{"name":"Jane Cooper","email":"jane@acme.com","message":"We want an e-commerce website to sell about 200 products with Stripe payments and a blog."}'
```

Sample fixtures for a detailed and a deliberately vague lead live in
`app/mocks/payloads.py` (`DETAILED_PAYLOAD`, `VAGUE_PAYLOAD`).

## Going live

Each integration has its own mode flag in `.env`, default `mock`:

```
LLM_MODE=mock     # "live" calls Gemini
EMAIL_MODE=mock   # "live" sends via Gmail SMTP
ODOO_MODE=mock    # "live" creates a real crm.lead
```

Flip to `live` once the matching credentials are filled in. Nothing else
changes — the webhook contract and response shape stay identical.

## Project layout

```
app/
├─ main.py            FastAPI app, /health, /webhook/lead, auth, orchestration
├─ schemas.py          Pydantic models + LeadCategory enum
├─ core/
│  ├─ config.py        settings + category→department map
│  └─ prompts.py        the single combined Gemini prompt
├─ services/
│  ├─ prefilter.py      normalization + junk detection
│  ├─ llm.py             Gemini call, JSON parse, fallback
│  ├─ emailer.py         Gmail SMTP + PDF attachment
│  └─ odoo.py            XML-RPC lead creation + dead-letter queue
├─ mocks/payloads.py    sample CF7-shaped fixtures
└─ assets/Company_Profile.pdf
scripts/make_pdf.py     generates the sample PDF
tests/                  pytest suite (18 tests, fully offline)
```

See `AI_LOGIC.md` for the prompt engineering strategy and reliability design.
