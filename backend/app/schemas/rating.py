from datetime import datetime
from pydantic import BaseModel


class EmployeePublicRatingOut(BaseModel):
    id: str
    user_id: str
    quarter: str
    year: int
    productivity_score: float
    task_completion_rate: float
    punctuality_score: float
    collaboration_score: float
    quality_score: float
    innovation_score: float
    overall_score: float
    rank_in_platform: int | None
    rank_in_org: int | None
    badge: str
    is_published: bool

    class Config:
        from_attributes = True


class OrgPublicRatingOut(BaseModel):
    id: str
    org_id: str
    quarter: str
    year: int
    avg_employee_score: float
    employee_retention_rate: float
    project_success_rate: float
    growth_rate: float
    activity_level: float
    support_rating: float
    overall_score: float
    rank_in_platform: int | None
    tier: str
    badge: str
    is_published: bool

    class Config:
        from_attributes = True


class EmployeeMonthlyRatingOut(BaseModel):
    id: str
    org_id: str
    user_id: str
    month: int
    year: int
    tasks_assigned: int
    tasks_completed: int
    tasks_overdue: int
    avg_task_time_hours: float
    total_active_hours: float
    total_idle_hours: float
    productive_app_ratio: float
    avg_daily_score: float
    overall_score: float
    rank_in_org: int | None
    rank_in_team: int | None
    trend: str
    manager_comment: str | None

    class Config:
        from_attributes = True
