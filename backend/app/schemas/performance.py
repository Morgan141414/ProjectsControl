from datetime import date

from pydantic import BaseModel, ConfigDict


class ActivityPerTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: str
    user_id: str
    start_date: date | None
    end_date: date | None
    team_id: str | None
    project_id: str | None
    tasks_total: int
    tasks_done: int
    observed_seconds: int
    active_seconds: int
    seconds_per_task: float
    active_seconds_per_task: float
