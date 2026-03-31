from datetime import datetime
from pydantic import BaseModel


class VacancyCreate(BaseModel):
    title: str
    team_id: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "RUB"
    experience_years: int = 0
    skills_required: list[str] = []
    employment_type: str = "full_time"


class VacancyUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    requirements: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    experience_years: int | None = None
    skills_required: list[str] | None = None
    employment_type: str | None = None
    is_active: bool | None = None


class VacancyOut(BaseModel):
    id: str
    org_id: str
    team_id: str | None
    title: str
    description: str | None
    requirements: str | None
    salary_min: int | None
    salary_max: int | None
    salary_currency: str
    experience_years: int
    skills_required_json: str | None
    employment_type: str
    is_active: bool
    views_count: int
    applications_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationCreate(BaseModel):
    cover_letter: str | None = None


class ApplicationUpdate(BaseModel):
    status: str


class ApplicationOut(BaseModel):
    id: str
    vacancy_id: str
    user_id: str
    cover_letter: str | None
    status: str
    ai_match_score: float | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True
