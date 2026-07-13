# How to Run This Project

`.env` is already set to live mode (`LLM_MODE=live`, `EMAIL_MODE=live`,
`ODOO_MODE=live`) with your real API keys — every run below calls the real
Gemini API, sends a real email, and creates a real lead in Odoo CRM.

## 1. Start the server

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Expected output ends with:
```
Uvicorn running on http://127.0.0.1:8000
```

Leave this window open. Press `Ctrl+C` to stop it.

If port 8000 is already in use:
```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```

## 2. Send a real lead — Swagger UI

Open in a browser: **http://127.0.0.1:8000/docs**

1. Click **`POST /webhook/lead`** → **"Try it out"**
2. In the **`X-Webhook-Secret`** field, paste the value of `WEBHOOK_SECRET`
   from `.env`
3. Paste a request body, e.g.:
   ```json
   {"name":"Jane Cooper","email":"akashbakshi.ai@gmail.com","message":"We want an e-commerce website to sell about 200 products with Stripe payments and a blog."}
   ```
4. Click **"Execute"**

This makes **one real Gemini call**, sends **one real email** (with the
Company Profile PDF attached) to the address you put in `"email"`, and
creates **one real lead** in Odoo CRM. Check your inbox and your Odoo
Leads list to confirm.

## 2b. Send a real lead — PowerShell

```powershell
$headers = @{ "X-Webhook-Secret" = "<value from your .env WEBHOOK_SECRET>" }
$body = @{
    name    = "Jane Cooper"
    email   = "akashbakshi.ai@gmail.com"
    message = "We want an e-commerce website to sell about 200 products with Stripe payments and a blog."
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhook/lead" -Method Post -Headers $headers -Body $body -ContentType "application/json"
```

## 3. Verify it landed

- **Email:** check the inbox of the address you used in `"email"` above —
  a reply with the Company Profile PDF attached and follow-up questions.
- **Odoo CRM:** log in at your `ODOO_URL` → **CRM** app → **Leads** → find
  the entry by contact name/email.

## 4. Edge cases

**Vague input:**
```json
{"name":"Sam Lee","email":"akashbakshi.ai@gmail.com","message":"Hi, I have an idea."}
```

**Junk/empty input** (no email/Odoo call is made, no cost):
```json
{"name":"x","email":"x@y.com","message":"   "}
```

**Wrong webhook secret** → `401 Unauthorized`, nothing runs.

## 5. Using your own Company Profile PDF

Copy your PDF into `app\assets\`, name it `Company_Profile.pdf` (overwrite
the existing one). No restart needed — it's read fresh on every email send.

## 6. Docker

```powershell
docker compose up --build
```

Builds and runs the same live service on port 8000.




# running commands
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000


# testing json.
{
  "name": "Jane Cooper",
  "email": "akashbakshi.ai@gmail.com",
  "message": "We want an e-commerce website to sell about 200 products with Stripe payments and a blog."
}




{
  "name": "Sam Lee",
  "email": "akashbakshi.ai@gmail.com",
  "message": "Hi, I have an idea."
}



{
  "name": "x",
  "email": "x@y.com",
  "message": "   "
}


python -m uvicorn app.main:app --host 127.0.0.1 --port 8000