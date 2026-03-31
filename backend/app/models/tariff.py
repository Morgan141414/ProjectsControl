from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import SupportLevel, SubscriptionStatus
from app.utils.ids import new_id


class TariffPlan(Base):
    __tablename__ = "tariff_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_monthly: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    price_yearly: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    # Limits
    max_employees: Mapped[int] = mapped_column(Integer, default=5)
    max_teams: Mapped[int] = mapped_column(Integer, default=1)
    max_projects: Mapped[int] = mapped_column(Integer, default=2)
    max_storage_gb: Mapped[int] = mapped_column(Integer, default=1)
    max_ai_tokens_monthly: Mapped[int] = mapped_column(Integer, default=10000)
    # Support
    support_level: Mapped[SupportLevel] = mapped_column(
        SAEnum(SupportLevel), default=SupportLevel.community
    )
    support_response_hours: Mapped[int] = mapped_column(Integer, default=72)
    # Feature flags
    has_ai_assistant: Mapped[bool] = mapped_column(Boolean, default=False)
    has_live_streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    has_export_reports: Mapped[bool] = mapped_column(Boolean, default=True)
    has_custom_branding: Mapped[bool] = mapped_column(Boolean, default=False)
    has_api_access: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video_calls: Mapped[bool] = mapped_column(Boolean, default=False)
    has_pdf_export: Mapped[bool] = mapped_column(Boolean, default=False)
    # Meta
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    tariff_plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("tariff_plans.id"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus), default=SubscriptionStatus.active
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=True)
    last_payment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("payments.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    organization = relationship("Organization", foreign_keys=[org_id])
    tariff_plan = relationship("TariffPlan", foreign_keys=[tariff_plan_id])
