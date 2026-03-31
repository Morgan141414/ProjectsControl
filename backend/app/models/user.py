from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.utils.ids import new_id


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))
    patronymic: Mapped[str | None] = mapped_column(String(100))
    bio: Mapped[str | None] = mapped_column(Text)
    specialty: Mapped[str | None] = mapped_column(String(120))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    gender: Mapped[str | None] = mapped_column(String(20))
    website: Mapped[str | None] = mapped_column(String(500))
    socials_json: Mapped[str | None] = mapped_column(Text)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Superadmin flag
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Professional data
    position: Mapped[str | None] = mapped_column(String(255))
    experience_years: Mapped[int | None] = mapped_column(Integer)
    skills_json: Mapped[str | None] = mapped_column(Text)  # JSON array
    experience_description: Mapped[str | None] = mapped_column(Text)
    education: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(String(50))
    city: Mapped[str | None] = mapped_column(String(100))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    resume_file: Mapped[str | None] = mapped_column(String(500))
    is_looking_for_job: Mapped[bool] = mapped_column(Boolean, default=False)
    desired_salary: Mapped[int | None] = mapped_column(Integer)
    questionnaire_score: Mapped[float | None] = mapped_column(Float)
    questionnaire_status: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    org_memberships = relationship(
        "OrgMembership", back_populates="user", cascade="all, delete-orphan"
    )
    team_memberships = relationship(
        "TeamMembership", back_populates="user", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="assignee")
