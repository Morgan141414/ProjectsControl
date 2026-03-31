from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import BanAppealStatus, BanType, PaymentProvider, PaymentStatus, PaymentType
from app.utils.ids import new_id


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    payment_type: Mapped[PaymentType] = mapped_column(SAEnum(PaymentType), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    provider: Mapped[PaymentProvider] = mapped_column(SAEnum(PaymentProvider), default=PaymentProvider.yookassa)
    external_id: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[str | None] = mapped_column(Text)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)

    user = relationship("User", foreign_keys=[user_id])


class UserBan(Base):
    __tablename__ = "user_bans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    banned_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    ban_type: Mapped[BanType] = mapped_column(SAEnum(BanType), default=BanType.temporary)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("payments.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    user = relationship("User", foreign_keys=[user_id])
    banned_by_user = relationship("User", foreign_keys=[banned_by])


class BanAppeal(Base):
    __tablename__ = "ban_appeals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ban_id: Mapped[str] = mapped_column(String(36), ForeignKey("user_bans.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[BanAppealStatus] = mapped_column(
        SAEnum(BanAppealStatus), default=BanAppealStatus.pending
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    payment_option: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    ban = relationship("UserBan", foreign_keys=[ban_id])
    user = relationship("User", foreign_keys=[user_id])
