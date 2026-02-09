from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AIScoreSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_id: str
    user_id: str
    period_type: str
    period_start: date
    period_end: date
    score: int
    completion_rate: float
    active_ratio: float
    tasks_total: int
    tasks_done: int
    observed_seconds: int
    idle_seconds: int
    active_seconds: int
    sessions_count: int
    generated_at: datetime


class AIScoreTrendPoint(BaseModel):
    period_start: date
    score: int


class AIScoreBaseline(BaseModel):
    avg_score: float
    avg_completion_rate: float
    avg_active_ratio: float
    avg_tasks_done: float


class AIChangeReason(BaseModel):
    code: str
    title: str
    detail: str
    delta: float


class AIDriverImpact(BaseModel):
    title: str
    detail: str
    impact_pct: float
    direction: str


class AIInterpretation(BaseModel):
    mode: str
    executive_summary: str
    vs_baseline: str
    primary_drivers: list[AIDriverImpact]
    trend: str
    suggestion: str | None
    stability: str | None = None
    team_median_score: float | None = None
    overload_risk: str | None = None


class AIScorecard(BaseModel):
    org_id: str
    user_id: str
    full_name: str
    period_type: str
    period_start: date
    period_end: date
    current: AIScoreSnapshotResponse
    baseline: AIScoreBaseline | None
    delta_score: float | None
    trend: list[AIScoreTrendPoint]
    reasons: list[AIChangeReason]
    interpretation: AIInterpretation | None = None


class AIScoreRebuildResponse(BaseModel):
    org_id: str
    period_type: str
    start_date: date
    end_date: date
    snapshots_count: int
