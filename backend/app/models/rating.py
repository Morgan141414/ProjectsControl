from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import BadgeLevel, OrgBadge, OrgTier, RatingTrend
from app.utils.ids import new_id


class EmployeePublicRating(Base):
    __tablename__ = "employee_public_ratings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    productivity_score: Mapped[float] = mapped_column(Float, default=0)
    task_completion_rate: Mapped[float] = mapped_column(Float, default=0)
    punctuality_score: Mapped[float] = mapped_column(Float, default=0)
    collaboration_score: Mapped[float] = mapped_column(Float, default=0)
    quality_score: Mapped[float] = mapped_column(Float, default=0)
    innovation_score: Mapped[float] = mapped_column(Float, default=0)
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    rank_in_platform: Mapped[int | None] = mapped_column(Integer)
    rank_in_org: Mapped[int | None] = mapped_column(Integer)
    badge: Mapped[BadgeLevel] = mapped_column(SAEnum(BadgeLevel), default=BadgeLevel.none)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class OrgPublicRating(Base):
    __tablename__ = "org_public_ratings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    quarter: Mapped[str] = mapped_column(String(10), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_employee_score: Mapped[float] = mapped_column(Float, default=0)
    employee_retention_rate: Mapped[float] = mapped_column(Float, default=0)
    project_success_rate: Mapped[float] = mapped_column(Float, default=0)
    growth_rate: Mapped[float] = mapped_column(Float, default=0)
    activity_level: Mapped[float] = mapped_column(Float, default=0)
    support_rating: Mapped[float] = mapped_column(Float, default=0)
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    rank_in_platform: Mapped[int | None] = mapped_column(Integer)
    tier: Mapped[OrgTier] = mapped_column(SAEnum(OrgTier), default=OrgTier.starter)
    badge: Mapped[OrgBadge] = mapped_column(SAEnum(OrgBadge), default=OrgBadge.none)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime)


class EmployeeMonthlyRating(Base):
    __tablename__ = "employee_monthly_ratings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    tasks_assigned: Mapped[int] = mapped_column(Integer, default=0)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_overdue: Mapped[int] = mapped_column(Integer, default=0)
    avg_task_time_hours: Mapped[float] = mapped_column(Float, default=0)
    total_active_hours: Mapped[float] = mapped_column(Float, default=0)
    total_idle_hours: Mapped[float] = mapped_column(Float, default=0)
    productive_app_ratio: Mapped[float] = mapped_column(Float, default=0)
    avg_daily_score: Mapped[float] = mapped_column(Float, default=0)
    flow_sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    burnout_risk: Mapped[float] = mapped_column(Float, default=0)
    reports_submitted: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    peer_reviews_given: Mapped[int] = mapped_column(Integer, default=0)
    peer_reviews_received: Mapped[int] = mapped_column(Integer, default=0)
    overall_score: Mapped[float] = mapped_column(Float, default=0)
    rank_in_org: Mapped[int | None] = mapped_column(Integer)
    rank_in_team: Mapped[int | None] = mapped_column(Integer)
    trend: Mapped[RatingTrend] = mapped_column(SAEnum(RatingTrend), default=RatingTrend.stable)
    manager_comment: Mapped[str | None] = mapped_column(Text)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime)
