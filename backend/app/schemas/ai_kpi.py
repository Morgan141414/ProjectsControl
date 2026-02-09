from datetime import date, datetime

from pydantic import BaseModel


class AIKPIUserScore(BaseModel):
    user_id: str
    full_name: str
    sessions_count: int
    tasks_total: int
    tasks_done: int
    completion_rate: float
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    active_ratio: float
    score: int


class AIKPIAnomaly(BaseModel):
    code: str
    severity: str
    title: str
    detail: str
    user_id: str | None = None


class AIKPIReport(BaseModel):
    org_id: str
    start_date: date | None
    end_date: date | None
    team_id: str | None
    project_id: str | None
    generated_at: datetime
    org_score: int
    users: list[AIKPIUserScore]
    anomalies: list[AIKPIAnomaly]
