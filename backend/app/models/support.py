from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import TicketCategory, TicketPriority, TicketStatus
from app.utils.ids import new_id


def _new_ticket_number() -> str:
    import uuid
    from datetime import datetime as dt
    return f"TICKET-{dt.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:5].upper()}"


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_number: Mapped[str] = mapped_column(String(50), unique=True, default=_new_ticket_number)
    org_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    category: Mapped[TicketCategory] = mapped_column(SAEnum(TicketCategory), default=TicketCategory.other)
    priority: Mapped[TicketPriority] = mapped_column(SAEnum(TicketPriority), default=TicketPriority.medium)
    status: Mapped[TicketStatus] = mapped_column(SAEnum(TicketStatus), default=TicketStatus.open)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    satisfaction_rating: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    author = relationship("User", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    messages = relationship("TicketMessage", back_populates="ticket", cascade="all, delete-orphan")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ticket_id: Mapped[str] = mapped_column(String(36), ForeignKey("support_tickets.id"), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False)
    attachments_json: Mapped[str | None] = mapped_column(Text)  # JSON array
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    ticket = relationship("SupportTicket", back_populates="messages")
    sender = relationship("User", foreign_keys=[sender_id])


class FAQArticle(Base):
    __tablename__ = "faq_articles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)
