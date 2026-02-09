from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    created_by: str
    report_type: str
    export_format: str
    size_bytes: int
    created_at: datetime


class ReportScheduleCreate(BaseModel):
    report_type: str = Field(min_length=3, max_length=50)
    interval_days: int = Field(ge=1, le=365)
    start_date: date | None = None
    end_date: date | None = None
    team_id: str | None = None
    project_id: str | None = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    created_by: str
    report_type: str
    interval_days: int
    enabled: bool
    last_run_at: datetime | None
    created_at: datetime
