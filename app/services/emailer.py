# import asyncio
# import os
# import smtplib
# from email.message import EmailMessage
# from tenacity import retry, stop_after_attempt, wait_exponential
# from app.schemas import NormalizedLead, AIResult
# from app.core.config import get_settings

# PDF_PATH = "app/assets/Company_Profile.pdf"


# def _questions_html(questions: list[str]) -> str:
#     items = "".join(f"<li>{q}</li>" for q in questions)
#     return f"<ul>{items}</ul>"


# def build_email(lead: NormalizedLead, ai: AIResult) -> EmailMessage:
#     settings = get_settings()
#     msg = EmailMessage()
#     msg["Subject"] = f"Thanks for contacting us about {ai.department}"
#     msg["From"] = settings.gmail_address
#     msg["To"] = lead.email # send mail to user email.
#     body = f"""<html><body>
# <p>Hi {lead.name or 'there'},</p>
# <p>Thanks for reaching out. We understand your inquiry as:
# <em>{ai.summary}</em>, which we handle in our <strong>{ai.department}</strong> team.</p>
# <p>To prepare an accurate proposal, could you help us with a few quick questions?</p>
# {_questions_html(ai.questions)}
# <p>Our Company Profile is attached. We'll be in touch shortly.</p>
# <p>Best regards,<br/>Bluechip Gulf Team</p>
# </body></html>"""
#     msg.set_content("Thanks for reaching out. Please view this email in HTML.")
#     msg.add_alternative(body, subtype="html")
#     if os.path.exists(PDF_PATH):
#         with open(PDF_PATH, "rb") as fh:
#             msg.add_attachment(
#                 fh.read(), maintype="application", subtype="pdf",
#                 filename="Company_Profile.pdf",
#             )
#     return msg


# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
# def _smtp_send(msg: EmailMessage) -> None:
#     settings = get_settings()
#     with smtplib.SMTP("smtp.gmail.com", 587) as server:
#         server.starttls()
#         server.login(settings.gmail_address, settings.gmail_app_password)
#         server.send_message(msg)# sending the message from company mail to user email.


# async def send_lead_email(lead: NormalizedLead, ai: AIResult) -> str:
#     settings = get_settings()
#     msg = build_email(lead, ai)
#     if settings.email_mode == "mock":
#         return "mock"
#     # smtplib is blocking (no async API), so run it in a worker thread
#     # to keep the event loop free.
#     print(f"Complete email JSON - {msg}")
#     await asyncio.to_thread(_smtp_send, msg)
#     return "sent"




import asyncio
import os
import smtplib
import ssl
from email.message import EmailMessage
from tenacity import retry, stop_after_attempt, wait_exponential
from app.schemas import NormalizedLead, AIResult
from app.core.config import get_settings

PDF_PATH = "app/assets/Company_Profile.pdf"


def _questions_html(questions: list[str]) -> str:
    items = "".join(f"<li>{q}</li>" for q in questions)
    return f"<ul>{items}</ul>"


def build_email(lead: NormalizedLead, ai: AIResult) -> EmailMessage:
    settings = get_settings()
    msg = EmailMessage()
    msg["Subject"] = f"Thanks for contacting us about {ai.department}"
    msg["From"] = settings.gmail_address
    msg["To"] = lead.email # send mail to user email.
    body = f"""<html><body>
<p>Hi {lead.name or 'there'},</p>
<p>Thanks for reaching out. We understand your inquiry as:
<em>{ai.summary}</em>, which we handle in our <strong>{ai.department}</strong> team.</p>
<p>To prepare an accurate proposal, could you help us with a few quick questions?</p>
{_questions_html(ai.questions)}
<p>Our Company Profile is attached. We'll be in touch shortly.</p>
<p>Best regards,<br/>Bluechip Gulf Team</p>
</body></html>"""
    msg.set_content("Thanks for reaching out. Please view this email in HTML.")
    msg.add_alternative(body, subtype="html")
    if os.path.exists(PDF_PATH):
        with open(PDF_PATH, "rb") as fh:
            msg.add_attachment(
                fh.read(), maintype="application", subtype="pdf",
                filename="Company_Profile.pdf",
            )
    return msg


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _smtp_send(msg: EmailMessage) -> None:
    settings = get_settings()
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=15) as server:
        server.login(settings.gmail_address, settings.gmail_app_password)
        server.send_message(msg)  # sending the message from company mail to user email.


async def send_lead_email(lead: NormalizedLead, ai: AIResult) -> str:
    settings = get_settings()
    msg = build_email(lead, ai)
    if settings.email_mode == "mock":
        return "mock"
    # smtplib is blocking (no async API), so run it in a worker thread
    # to keep the event loop free.
    print(f"Complete email JSON - {msg}")
    await asyncio.to_thread(_smtp_send, msg)
    return "sent"
