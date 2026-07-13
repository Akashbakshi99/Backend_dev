from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.schemas import LeadCategory

DEPARTMENT_MAP: dict[LeadCategory, str] = {
    LeadCategory.web_development: "Web",
    LeadCategory.mobile_development: "Mobile",
    LeadCategory.ai_automation: "AI/Automation",
    LeadCategory.consulting: "Consulting",
    LeadCategory.needs_clarification: "Other (Review)",
    LeadCategory.other: "Other",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    webhook_secret: str = "change-me"
    gemini_api_key: str = ""
    gmail_address: str = "akashbakshi.ai@gmail.com"
    gmail_app_password: str = ""
    odoo_url: str = ""
    odoo_db: str = ""
    odoo_username: str = "akashbakshi.ai@gmail.com"
    odoo_api_key: str = ""

    llm_mode: str = "mock"
    email_mode: str = "mock"
    odoo_mode: str = "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
