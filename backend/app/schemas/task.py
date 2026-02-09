from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    due_date: date | None = None
    assignee_id: str | None = None
    team_id: str | None = None


class TaskUpdate(BaseModel):
    status: TaskStatus | None = None
    report: str | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    team_id: str | None
    assignee_id: str | None
    title: str
    description: str | None
    status: TaskStatus
    report: str | None
    due_date: date | None
    created_at: datetime
