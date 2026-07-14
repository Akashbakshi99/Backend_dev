from enum import Enum
from pydantic import BaseModel, EmailStr, Field


class LeadCategory(str, Enum):
    web_development = "web_development"
    mobile_development = "mobile_development"
    ai_automation = "ai_automation"
    consulting = "consulting"
    needs_clarification = "needs_clarification"
    other = "other"


class InboundForm(BaseModel):
    name: str
    email: EmailStr
    message: str
    subject: str | None = None
    phone: str | None = None


class NormalizedLead(BaseModel):
    name: str
    email: str
    message: str
    subject: str | None = None
    phone: str | None = None


class AIResult(BaseModel):
    intent: str
    category: LeadCategory
    department: str
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    questions: list[str]
