# Run & Test Guide — AI Lead Automation

Everything needed to set up, run, test, and verify the service end-to-end.

---

## 1. Prerequisites

- Python 3.11+
- The dependencies in `requirements.txt`

```bash
pip install -r requirements.txt
```

---

## 2. Environment variables (`.env`)

Create a `.env` file in the project root:

```
# Webhook auth
WEBHOOK_SECRET=<a-long-random-string>

# Google Gemini (LLM)
GEMINI_API_KEY=<your-gemini-key>

# Gmail (auto-reply email)
GMAIL_ADDRESS=<your-gmail-address>
GMAIL_APP_PASSWORD=<16-char-gmail-app-password>

# Odoo CRM
ODOO_URL=https://<your-db>.odoo.com
ODOO_DB=<your-db>
ODOO_USERNAME=<your-odoo-login-email>
ODOO_API_KEY=<your-odoo-api-key>

# Integration modes: "mock" (default) or "live"
LLM_MODE=live
EMAIL_MODE=live
ODOO_MODE=live
```

**Modes** — each integration is independent:

| Flag | `mock` | `live` |
|---|---|---|
| `LLM_MODE` | keyword heuristic, no API call | real Google Gemini call |
| `EMAIL_MODE` | no email sent (returns "mock") | real Gmail SMTP send |
| `ODOO_MODE` | no CRM write (returns "mock-…") | real `crm.lead` created |

All three default to `mock`, so the full pipeline runs offline with zero cost until you flip
them to `live`.

---

## 3. Run the service

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

- Health check: `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
- Webhook: `POST http://127.0.0.1:8000/webhook/lead`
- Interactive API docs: `http://127.0.0.1:8000/docs`

> After changing code or `.env`, restart the server (or run with `--reload`) so the new values load.

---

## 4. How the webhook works (per request)

1. Auth: `X-Webhook-Secret` header must match `WEBHOOK_SECRET` (else `401`).
2. Validate + normalize the form (name, email, message, optional `phone`).
3. Junk filter: empty/garbage messages return `{"status":"ignored"}` — no API call spent.
4. AI classify (one Gemini call): `intent`, `category`, `confidence`, `summary`, 3–6 questions.
5. Response returned immediately, then two background tasks run:
   - Email the prospect (contextual reply + Company Profile PDF + AI questions)
   - Log the lead in Odoo `crm.lead`, routed to the correct **Sales Team** (department)

**Dynamic fields written to the Odoo lead:**

| Odoo field | Source |
|---|---|
| Sales Team (`team_id`) | department, derived from AI `category` |
| Phone | taken from the payload's `phone` (dynamic; omitted if not sent) |
| Priority | derived from AI `confidence`: ≥0.8 Very High, ≥0.6 High, ≥0.4 Medium, else Low |
| Contact name | payload `name` |
| Email | payload `email` |
| Description | routing note + intent + confidence + original message + AI questions |

---

## 5. Test with curl

Replace `<SECRET>` with your `WEBHOOK_SECRET`.

```bash
curl -X POST http://127.0.0.1:8000/webhook/lead \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: <SECRET>" \
  -d '{
    "name": "Ravi Shah",
    "email": "akashbakshi.ai@gmail.com",
    "phone": "+91 98200 45678",
    "message": "We need a mobile app for iOS and Android so customers can book appointments."
  }'
```

Or use the Swagger UI at `/docs` → `POST /webhook/lead` → "Try it out".

---

## 6. Test payloads (three per department + edge cases)

`phone` is **dynamic** — the service writes whatever number the payload carries. The numbers below
are sample customer numbers; replace with any real value and that exact value lands in Odoo.

### Web  → team **Web**

```json
{
  "name": "Jane Cooper",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+91 8899457781",
  "message": "We want an e-commerce website to sell about 200 products with Stripe payments and a blog."
}
```

```json
{
  "name": "Leo Martins",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+1 312 447 8820",
  "message": "Our current WordPress site is outdated. We want a redesigned company website with a booking form and blog."
}
```

```json
{
  "name": "Hannah Weber",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+44 20 7946 0958",
  "message": "We want a custom online store built on Shopify with a product catalog and secure checkout."
}
```

### Mobile  → team **Mobile**

```json
{
  "name": "Ravi Shah",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+91 98200 45678",
  "message": "We need a mobile app for iOS and Android so customers can book appointments."
}
```

```json
{
  "name": "Aisha Khan",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+971 50 123 4567",
  "message": "Looking to build an Android and iOS delivery tracking app with live GPS and push notifications."
}
```

```json
{
  "name": "Diego Alvarez",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+61 2 8123 4567",
  "message": "We are launching a food delivery startup and need a native iOS and Android app with real-time order tracking."
}
```

### AI/Automation  → team **AI/Automation**

```json
{
  "name": "Meera Kapoor",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+91 99870 33421",
  "message": "We want to automate our customer support with an AI-powered chatbot."
}
```

```json
{
  "name": "Tom Becker",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+1 206 774 1190",
  "message": "We want an AI chatbot and workflow automation to handle repetitive email replies for our support team."
}
```

```json
{
  "name": "Yuki Tanaka",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+49 30 1234 5678",
  "message": "We would like to build an LLM-based assistant to automate invoice processing and data entry."
}
```

### Consulting  → team **Consulting**

```json
{
  "name": "David Chen",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+65 8123 4567",
  "message": "We run an established logistics business and want expert consulting on our internal processes, vendor contracts, and overall technology roadmap for the next few years."
}
```

```json
{
  "name": "Sara Oliveira",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+55 11 96321 8890",
  "message": "We are a mid-sized manufacturing firm seeking strategic guidance on our overall digital transformation roadmap, team structure, and long-term technology investments."
}
```

```json
{
  "name": "Omar Farouk",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+971 4 555 0132",
  "message": "Our logistics firm wants expert guidance on scaling operations, hiring strategy, and selecting the best software vendors for the next year."
}
```

### Other  → team **Other**

```json
{
  "name": "Priya Nair",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+91 98765 43210",
  "message": "Can you help us source commercial furniture and office fit-out for our new branch?"
}
```

```json
{
  "name": "Marco Rossi",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+39 340 118 2299",
  "message": "Do you provide printed marketing brochures and branded merchandise for corporate events?"
}
```

```json
{
  "name": "Grace Mensah",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+91 80 4123 6789",
  "message": "Do you offer event photography and video production services for our annual conference?"
}
```

> Note: in `LLM_MODE=mock` there is no dedicated "other" heuristic, so the "Other" examples
> classify as **Consulting** locally. Live Gemini (`LLM_MODE=live`) returns **other** for requests
> clearly outside Web/Mobile/AI-Automation/Consulting.

### Edge case — vague input (→ `needs_clarification` → team **Other**)

```json
{
  "name": "Sam Lee",
  "email": "akashbakshi.ai@gmail.com",
  "phone": "+1 646 220 7788",
  "message": "Hi, I have an idea."
}
```

### Edge case — junk / empty input (ignored, no API call, no email, no lead)

```json
{
  "name": "x",
  "email": "x@y.com",
  "message": "   "
}
```

Expected response: `{"status":"ignored","reason":"junk"}`

---

## 7. Expected webhook response (accepted lead)

```json
{
  "status": "accepted",
  "department": "Mobile",
  "category": "mobile_development",
  "summary": "Development of a cross-platform mobile app for appointment scheduling.",
  "questions": [
    "Do you have an existing backend system or API for appointment management?",
    "Do you require user authentication and profile management features?",
    "Will the app need to integrate with third-party calendars like Google or Outlook?",
    "Do you need push notifications for appointment reminders?",
    "What is your target timeline for the MVP launch?"
  ]
}
```

---

## 8. Run the automated tests

Fully offline (all modes default to `mock`), zero API calls:

```bash
pytest -v
```

Covers: prefilter/junk, schema validation, LLM parsing + fallback, email building, Odoo payload
building (routing, phone, priority), and a full webhook integration test.

---

## 9. Verify routing in Odoo

1. Open the **CRM** app in Odoo.
2. Enable **Leads** if hidden: **CRM → Configuration → Settings → tick "Leads"**.
3. Go to **CRM → Leads** (API-created records are type `lead`, not in the Pipeline kanban).
4. In the list, **Group By → Sales Team** to see leads bucketed by department:
   `Web`, `Mobile`, `AI/Automation`, `Consulting`, `Other`.
5. Open a lead to confirm **Phone** and **Priority** (stars) are populated.




<!-- python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 -->