from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.utils.ids import new_id


class AICompanyAssistant(Base):
    __tablename__ = "ai_company_assistants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), unique=True, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str] = mapped_column(String(100), default="claude-sonnet-4-20250514")
    monthly_tokens_limit: Mapped[int] = mapped_column(Integer, default=1_000_000)
    tokens_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    context_json: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    organization = relationship("Organization", foreign_keys=[org_id])


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    messages_json: Mapped[str | None] = mapped_column(Text)  # JSON
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    organization = relationship("Organization", foreign_keys=[org_id])
    user = relationship("User", foreign_keys=[user_id])
