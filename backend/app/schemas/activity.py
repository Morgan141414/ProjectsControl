from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ActivityType, AuditAction, SessionStatus


class SessionStart(BaseModel):
    device_name: str | None = Field(default=None, max_length=255)
    os_name: str | None = Field(default=None, max_length=255)


class SessionStop(BaseModel):
    ended_at: datetime | None = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    user_id: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    device_name: str | None
    os_name: str | None


class ActivityEventCreate(BaseModel):
    session_id: str
    event_type: ActivityType
    captured_at: datetime | None = None
    app_name: str | None = None
    window_title: str | None = None
    idle_seconds: int | None = None
    notes: str | None = None


class ActivityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    org_id: str
    user_id: str
    event_type: ActivityType
    captured_at: datetime
    app_name: str | None
    window_title: str | None
    idle_seconds: int | None
    notes: str | None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    actor_id: str
    action: AuditAction
    entity_type: str
    entity_id: str
    created_at: datetime
    details: str | None


class RecordingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    org_id: str
    user_id: str
    content_type: str | None
    size_bytes: int
    checksum_sha256: str
    created_at: datetime


class RecordingCleanupResponse(BaseModel):
    deleted_count: int
    retention_days: int


class EventsCleanupResponse(BaseModel):
    deleted_count: int
    retention_days: int
