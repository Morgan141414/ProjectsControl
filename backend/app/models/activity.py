from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import ActivityType, AuditAction, SessionStatus
from app.utils.ids import new_id


class ScreenSession(Base):
    __tablename__ = "screen_sessions"
    __table_args__ = (
        Index("ix_screen_sessions_org_user", "org_id", "user_id"),
        Index("ix_screen_sessions_org_started", "org_id", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), default=SessionStatus.active)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    device_name: Mapped[str | None] = mapped_column(String(255))
    os_name: Mapped[str | None] = mapped_column(String(255))

    user = relationship("User")
    organization = relationship("Organization")
    events = relationship(
        "ActivityEvent", back_populates="session", cascade="all, delete-orphan"
    )
    recordings = relationship(
        "ScreenRecording", back_populates="session", cascade="all, delete-orphan"
    )


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_session_captured", "session_id", "captured_at"),
        Index("ix_activity_events_org_user_captured", "org_id", "user_id", "captured_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("screen_sessions.id"), index=True)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    event_type: Mapped[ActivityType] = mapped_column(SAEnum(ActivityType))
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive, index=True)
    app_name: Mapped[str | None] = mapped_column(String(255))
    window_title: Mapped[str | None] = mapped_column(String(255))
    idle_seconds: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)

    session = relationship("ScreenSession", back_populates="events")
    user = relationship("User")
    organization = relationship("Organization")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    actor_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[AuditAction] = mapped_column(SAEnum(AuditAction))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    details: Mapped[str | None] = mapped_column(Text)

    actor = relationship("User")
    organization = relationship("Organization")


class ScreenRecording(Base):
    __tablename__ = "screen_recordings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("screen_sessions.id"))
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    file_path: Mapped[str] = mapped_column(String(500))
    content_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    session = relationship("ScreenSession", back_populates="recordings")
    user = relationship("User")
    organization = relationship("Organization")
