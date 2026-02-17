from datetime import datetime
from pydantic import BaseModel


class TariffPlanOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None
    price_monthly: float
    price_yearly: float
    currency: str
    max_employees: int
    max_teams: int
    max_projects: int
    max_storage_gb: int
    max_ai_tokens_monthly: int
    support_level: str
    support_response_hours: int
    has_ai_assistant: bool
    has_live_streaming: bool
    has_export_reports: bool
    has_custom_branding: bool
    has_api_access: bool
    has_video_calls: bool
    has_pdf_export: bool
    is_active: bool

    class Config:
        from_attributes = True


class TariffPlanCreate(BaseModel):
    name: str
    code: str
    description: str | None = None
    price_monthly: float = 0
    price_yearly: float = 0
    max_employees: int = 5
    max_teams: int = 1
    max_projects: int = 2
    max_storage_gb: int = 1
    max_ai_tokens_monthly: int = 10000
    support_level: str = "community"
    has_ai_assistant: bool = False
    has_video_calls: bool = False


class SubscriptionOut(BaseModel):
    id: str
    org_id: str
    tariff_plan_id: str
    status: str
    starts_at: datetime
    ends_at: datetime
    auto_renew: bool
    created_at: datetime

    class Config:
        from_attributes = True
