from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyReportCreate(BaseModel):
    project_id: str
    report_date: date | None = None
    content: str = Field(min_length=1)


class DailyReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    project_id: str
    user_id: str
    report_date: date
    content: str
    created_at: datetime
