from datetime import datetime
from pydantic import BaseModel


class VideoRoomCreate(BaseModel):
    name: str
    room_type: str = "group"
    max_participants: int = 10
    scheduled_at: datetime | None = None


class VideoRoomOut(BaseModel):
    id: str
    org_id: str
    name: str
    room_type: str
    created_by: str
    max_participants: int
    is_recording: bool
    is_active: bool
    scheduled_at: datetime | None
    started_at: datetime | None
    ended_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class VideoParticipantOut(BaseModel):
    id: str
    room_id: str
    user_id: str
    role: str
    is_muted: bool
    is_camera_on: bool
    is_screen_sharing: bool
    joined_at: datetime
    left_at: datetime | None

    class Config:
        from_attributes = True
