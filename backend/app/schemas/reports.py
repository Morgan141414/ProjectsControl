from datetime import date

from pydantic import BaseModel, ConfigDict


class KPIUserRow(BaseModel):
    user_id: str
    full_name: str
    sessions_count: int
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    tasks_total: int
    tasks_done: int
    completion_rate: float


class KPITeamRow(BaseModel):
    team_id: str
    team_name: str
    users_count: int
    sessions_count: int
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    tasks_total: int
    tasks_done: int
    completion_rate: float


class KPIOrgReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: str
    start_date: date | None
    end_date: date | None
    total_users: int
    total_sessions: int
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    tasks_total: int
    tasks_done: int
    completion_rate: float
    users: list[KPIUserRow]
    teams: list[KPITeamRow]
