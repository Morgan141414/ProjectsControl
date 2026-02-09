from datetime import date

from pydantic import BaseModel, ConfigDict


class ProjectKPIItem(BaseModel):
    project_id: str
    project_name: str
    teams_count: int
    users_count: int
    sessions_count: int
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    tasks_total: int
    tasks_done: int
    completion_rate: float


class ProjectKPIReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: str
    start_date: date | None
    end_date: date | None
    projects: list[ProjectKPIItem]
