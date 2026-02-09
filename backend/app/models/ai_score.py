from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ScorePeriod
from app.utils.ids import new_id


class AIScoreSnapshot(Base):
    __tablename__ = "ai_score_snapshots"
    __table_args__ = (
        UniqueConstraint("org_id", "user_id", "period_type", "period_start", "period_end", name="uq_ai_score_period"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    period_type: Mapped[ScorePeriod] = mapped_column(SAEnum(ScorePeriod))
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    score: Mapped[int] = mapped_column(Integer)
    completion_rate: Mapped[float] = mapped_column(Float)
    active_ratio: Mapped[float] = mapped_column(Float)
    tasks_total: Mapped[int] = mapped_column(Integer)
    tasks_done: Mapped[int] = mapped_column(Integer)
    observed_seconds: Mapped[int] = mapped_column(Integer)
    idle_seconds: Mapped[int] = mapped_column(Integer)
    active_seconds: Mapped[int] = mapped_column(Integer)
    sessions_count: Mapped[int] = mapped_column(Integer)
    reasons_json: Mapped[str | None] = mapped_column(Text)
    drivers_json: Mapped[str | None] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    organization = relationship("Organization")
