from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import MatchType, PrivacyAction, PrivacyTarget
from app.utils.ids import new_id


class PrivacyRule(Base):
    __tablename__ = "privacy_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    target: Mapped[PrivacyTarget] = mapped_column(SAEnum(PrivacyTarget))
    match_type: Mapped[MatchType] = mapped_column(SAEnum(MatchType))
    pattern: Mapped[str] = mapped_column(Text)
    action: Mapped[PrivacyAction] = mapped_column(SAEnum(PrivacyAction))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
