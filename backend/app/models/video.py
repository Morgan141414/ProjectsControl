from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import VideoParticipantRole, VideoRoomType
from app.utils.ids import new_id


class VideoRoom(Base):
    __tablename__ = "video_rooms"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    room_type: Mapped[VideoRoomType] = mapped_column(
        SAEnum(VideoRoomType), default=VideoRoomType.group
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    max_participants: Mapped[int] = mapped_column(Integer, default=10)
    is_recording: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    organization = relationship("Organization", foreign_keys=[org_id])
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("VideoParticipant", back_populates="room", cascade="all, delete-orphan")


class VideoParticipant(Base):
    __tablename__ = "video_participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("video_rooms.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role: Mapped[VideoParticipantRole] = mapped_column(
        SAEnum(VideoParticipantRole), default=VideoParticipantRole.participant
    )
    is_muted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_camera_on: Mapped[bool] = mapped_column(Boolean, default=True)
    is_screen_sharing: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    left_at: Mapped[datetime | None] = mapped_column(DateTime)

    room = relationship("VideoRoom", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])


class VideoRecording(Base):
    __tablename__ = "video_recordings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("video_rooms.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    room = relationship("VideoRoom", foreign_keys=[room_id])
