from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import ApplicationStatus, EmploymentType
from app.utils.ids import new_id


class Vacancy(Base):
    __tablename__ = "vacancies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    salary_min: Mapped[int | None] = mapped_column(Integer)
    salary_max: Mapped[int | None] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String(10), default="RUB")
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    skills_required_json: Mapped[str | None] = mapped_column(Text)  # JSON array
    employment_type: Mapped[EmploymentType] = mapped_column(
        SAEnum(EmploymentType), default=EmploymentType.full_time
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    applications_count: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime)

    organization = relationship("Organization", foreign_keys=[org_id])
    team = relationship("Team", foreign_keys=[team_id])
    applications = relationship("VacancyApplication", back_populates="vacancy", cascade="all, delete-orphan")


class VacancyApplication(Base):
    __tablename__ = "vacancy_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    vacancy_id: Mapped[str] = mapped_column(String(36), ForeignKey("vacancies.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus), default=ApplicationStatus.pending
    )
    ai_match_score: Mapped[float | None] = mapped_column(Float)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    vacancy = relationship("Vacancy", back_populates="applications")
    user = relationship("User", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
