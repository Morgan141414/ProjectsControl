from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AppUsageItem(BaseModel):
    app_name: str
    seconds: int
    events: int


class SessionMetricsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    org_id: str
    user_id: str
    started_at: datetime
    ended_at: datetime | None
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    app_usage: list[AppUsageItem]


class UserMetricsResponse(BaseModel):
    org_id: str
    user_id: str
    start_date: date | None
    end_date: date | None
    sessions_count: int
    total_events: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    app_usage: list[AppUsageItem]
