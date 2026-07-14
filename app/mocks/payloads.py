"""Sample WordPress/CF7-shaped form payloads for local testing and the test suite.

`phone` is optional on the inbound form; when present it flows straight through to the
Odoo lead's Phone field (nothing is hardcoded in the app — see services/odoo.py).
"""

DETAILED_PAYLOAD = {
    "name": "Jane Cooper",
    "email": "akashbakshi.ai@gmail.com",
    "phone": "+1 415 892 0134",
    "message": "We want an e-commerce website to sell about 200 products with Stripe payments and a blog.",
}

VAGUE_PAYLOAD = {
    "name": "Sam Lee",
    "email": "akashbakshi.ai@gmail.com",
    "phone": "+1 646 220 7788",
    "message": "Hi, I have an idea.",
}
