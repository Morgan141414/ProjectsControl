import json
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.reports import compute_org_kpi_report
from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.activity import ActivityEvent, ScreenSession
from app.models.ai_score import AIScoreSnapshot
from app.models.enums import ActivityType, OrgRole, ScorePeriod
from app.models.user import User
from app.schemas.ai_kpi import AIKPIAnomaly, AIKPIReport, AIKPIUserScore
from app.schemas.ai_score import (
    AIDriverImpact,
    AIChangeReason,
    AIInterpretation,
    AIScoreBaseline,
    AIScoreRebuildResponse,
    AIScoreSnapshotResponse,
    AIScoreTrendPoint,
    AIScorecard,
)

router = APIRouter(prefix="/orgs/{org_id}/ai", tags=["ai"])


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _score_user(row) -> tuple[int, float]:
    active_ratio = _safe_ratio(row.active_seconds, row.observed_seconds)
    tasks_factor = min(row.tasks_done / 5, 1.0) if row.tasks_done else 0.0
    score = int(round(100 * (0.45 * row.completion_rate + 0.35 * active_ratio + 0.2 * tasks_factor)))
    score = max(0, min(score, 100))
    return score, active_ratio


def _median(values: list[int]) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    mid = len(values_sorted) // 2
    if len(values_sorted) % 2 == 1:
        return float(values_sorted[mid])
    return (values_sorted[mid - 1] + values_sorted[mid]) / 2.0


def _period_bounds(as_of: date, period: ScorePeriod) -> tuple[date, date]:
    if period == ScorePeriod.weekly:
        start = as_of - timedelta(days=as_of.weekday())
        end = start + timedelta(days=6)
        return start, end
    return as_of, as_of


def _iter_periods(start_date: date, end_date: date, period: ScorePeriod) -> list[tuple[date, date]]:
    if start_date > end_date:
        return []

    periods: list[tuple[date, date]] = []
    if period == ScorePeriod.weekly:
        current_start = start_date - timedelta(days=start_date.weekday())
        while current_start <= end_date:
            current_end = current_start + timedelta(days=6)
            if current_end < start_date:
                current_start += timedelta(days=7)
                continue
            periods.append((max(current_start, start_date), min(current_end, end_date)))
            current_start += timedelta(days=7)
        return periods

    current_day = start_date
    while current_day <= end_date:
        periods.append((current_day, current_day))
        current_day += timedelta(days=1)
    return periods


def _cap_delta(delta_seconds: float) -> int:
    if delta_seconds <= 0:
        return 0
    if delta_seconds > settings.METRICS_MAX_GAP_SECONDS:
        return settings.METRICS_MAX_GAP_SECONDS
    return int(delta_seconds)


def _load_user_events(
    db: Session,
    org_id: str,
    user_id: str,
    start_date: date,
    end_date: date,
) -> list[ActivityEvent]:
    sessions_query = db.query(ScreenSession).filter(
        ScreenSession.org_id == org_id,
        ScreenSession.user_id == user_id,
        ScreenSession.started_at >= datetime.combine(start_date, datetime.min.time()),
        ScreenSession.started_at <= datetime.combine(end_date, datetime.max.time()),
    )
    sessions = sessions_query.all()
    if not sessions:
        return []
    session_ids = [session.id for session in sessions]
    return (
        db.query(ActivityEvent)
        .filter(ActivityEvent.session_id.in_(session_ids))
        .order_by(ActivityEvent.captured_at.asc())
        .all()
    )


def _classify_app(app_name: str | None) -> str | None:
    if not app_name:
        return None
    name = app_name.lower()
    if any(token in name for token in ("code", "pycharm", "intellij", "webstorm", "idea", "visual studio", "vim", "emacs")):
        return "ide"
    if any(token in name for token in ("jira", "trello", "asana", "clickup", "youtrack")):
        return "planning"
    if any(token in name for token in ("slack", "teams", "telegram", "discord", "zoom", "meet", "skype", "outlook")):
        return "communication"
    if any(token in name for token in ("confluence", "notion", "wiki", "docs", "chrome", "firefox", "edge", "safari")):
        return "docs"
    return "other"


def _compute_driver_metrics(
    db: Session,
    org_id: str,
    user_id: str,
    start_date: date,
    end_date: date,
) -> dict[str, float]:
    events = _load_user_events(db, org_id, user_id, start_date, end_date)
    if len(events) < 2:
        return {
            "context_switches_per_hour": 0.0,
            "deep_work_ratio": 0.0,
            "communication_ratio": 0.0,
            "planning_ratio": 0.0,
            "docs_ratio": 0.0,
            "ide_ratio": 0.0,
        }

    observed_seconds = 0
    idle_seconds = 0
    switches = 0
    usage: dict[str, int] = {}

    for index in range(len(events) - 1):
        current = events[index]
        next_event = events[index + 1]
        delta = _cap_delta((next_event.captured_at - current.captured_at).total_seconds())
        if delta == 0:
            continue
        observed_seconds += delta

        if current.event_type == ActivityType.idle:
            if current.idle_seconds is not None:
                idle_seconds += min(current.idle_seconds, delta)
            else:
                idle_seconds += delta
        else:
            if current.app_name:
                usage[current.app_name] = usage.get(current.app_name, 0) + delta

        if current.app_name and next_event.app_name and current.app_name != next_event.app_name:
            switches += 1

    active_seconds = max(observed_seconds - idle_seconds, 0)
    if active_seconds <= 0:
        return {
            "context_switches_per_hour": 0.0,
            "deep_work_ratio": 0.0,
            "communication_ratio": 0.0,
            "planning_ratio": 0.0,
            "docs_ratio": 0.0,
            "ide_ratio": 0.0,
        }

    category_seconds = {"ide": 0, "docs": 0, "communication": 0, "planning": 0}
    for app_name, seconds in usage.items():
        category = _classify_app(app_name)
        if category in category_seconds:
            category_seconds[category] += seconds

    ide_ratio = category_seconds["ide"] / active_seconds
    docs_ratio = category_seconds["docs"] / active_seconds
    communication_ratio = category_seconds["communication"] / active_seconds
    planning_ratio = category_seconds["planning"] / active_seconds
    deep_work_ratio = min(1.0, ide_ratio + docs_ratio * 0.5)
    switches_per_hour = switches / max(observed_seconds / 3600, 1)

    return {
        "context_switches_per_hour": switches_per_hour,
        "deep_work_ratio": deep_work_ratio,
        "communication_ratio": communication_ratio,
        "planning_ratio": planning_ratio,
        "docs_ratio": docs_ratio,
        "ide_ratio": ide_ratio,
    }


def _tasks_factor(tasks_done: int) -> float:
    if tasks_done <= 0:
        return 0.0
    return min(tasks_done / 5, 1.0)


def _upsert_snapshot(
    db: Session,
    org_id: str,
    period_type: ScorePeriod,
    period_start: date,
    period_end: date,
    user_row,
) -> AIScoreSnapshot:
    score, active_ratio = _score_user(user_row)
    driver_metrics = _compute_driver_metrics(db, org_id, user_row.user_id, period_start, period_end)
    drivers_json = json.dumps(driver_metrics, ensure_ascii=True)
    existing = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_row.user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start == period_start,
            AIScoreSnapshot.period_end == period_end,
        )
        .first()
    )

    if existing:
        snapshot = existing
    else:
        snapshot = AIScoreSnapshot(
            org_id=org_id,
            user_id=user_row.user_id,
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            score=score,
            completion_rate=user_row.completion_rate,
            active_ratio=active_ratio,
            tasks_total=user_row.tasks_total,
            tasks_done=user_row.tasks_done,
            observed_seconds=user_row.observed_seconds,
            idle_seconds=user_row.idle_seconds,
            active_seconds=user_row.active_seconds,
            sessions_count=user_row.sessions_count,
            drivers_json=drivers_json,
        )
        db.add(snapshot)

    snapshot.score = score
    snapshot.completion_rate = user_row.completion_rate
    snapshot.active_ratio = active_ratio
    snapshot.tasks_total = user_row.tasks_total
    snapshot.tasks_done = user_row.tasks_done
    snapshot.observed_seconds = user_row.observed_seconds
    snapshot.idle_seconds = user_row.idle_seconds
    snapshot.active_seconds = user_row.active_seconds
    snapshot.sessions_count = user_row.sessions_count
    snapshot.drivers_json = drivers_json
    snapshot.generated_at = datetime.utcnow()

    return snapshot


def _load_trend(
    db: Session,
    org_id: str,
    user_id: str,
    period_type: ScorePeriod,
    period_start: date,
    limit: int,
) -> list[AIScoreTrendPoint]:
    if limit <= 0:
        return []

    snapshots = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start <= period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(limit)
        .all()
    )
    snapshots.reverse()
    return [AIScoreTrendPoint(period_start=item.period_start, score=item.score) for item in snapshots]


def _load_baseline(
    db: Session,
    org_id: str,
    user_id: str,
    period_type: ScorePeriod,
    period_start: date,
) -> AIScoreBaseline | None:
    baseline_limit = 7 if period_type == ScorePeriod.daily else 4
    snapshots = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start < period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(baseline_limit)
        .all()
    )

    if not snapshots:
        return None

    avg_score = sum(item.score for item in snapshots) / len(snapshots)
    avg_completion = sum(item.completion_rate for item in snapshots) / len(snapshots)
    avg_active = sum(item.active_ratio for item in snapshots) / len(snapshots)
    avg_tasks = sum(item.tasks_done for item in snapshots) / len(snapshots)

    return AIScoreBaseline(
        avg_score=avg_score,
        avg_completion_rate=avg_completion,
        avg_active_ratio=avg_active,
        avg_tasks_done=avg_tasks,
    )


def _build_reasons(current: AIScoreSnapshot, baseline: AIScoreBaseline | None) -> list[AIChangeReason]:
    if not baseline:
        return []

    completion_delta = current.completion_rate - baseline.avg_completion_rate
    active_delta = current.active_ratio - baseline.avg_active_ratio
    tasks_delta = _tasks_factor(current.tasks_done) - _tasks_factor(int(round(baseline.avg_tasks_done)))

    completion_points = completion_delta * 100 * 0.45
    active_points = active_delta * 100 * 0.35
    tasks_points = tasks_delta * 100 * 0.2

    reasons = [
        AIChangeReason(
            code="completion_rate",
            title="Завершение задач",
            detail=f"Изменение доли выполненных задач на {completion_delta * 100:.1f}%.",
            delta=completion_points,
        ),
        AIChangeReason(
            code="focus_ratio",
            title="Концентрация",
            detail=f"Изменение доли активного времени на {active_delta * 100:.1f}%.",
            delta=active_points,
        ),
        AIChangeReason(
            code="task_volume",
            title="Объем задач",
            detail=f"Изменение выполненных задач на {current.tasks_done - baseline.avg_tasks_done:.1f}.",
            delta=tasks_points,
        ),
    ]

    threshold = 1.5
    filtered = [item for item in reasons if abs(item.delta) >= threshold]
    filtered.sort(key=lambda item: abs(item.delta), reverse=True)
    return filtered[:3]


def _load_driver_baseline(
    db: Session,
    org_id: str,
    user_id: str,
    period_type: ScorePeriod,
    period_start: date,
) -> dict[str, float] | None:
    baseline_limit = 7 if period_type == ScorePeriod.daily else 4
    snapshots = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start < period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(baseline_limit)
        .all()
    )
    metrics: dict[str, list[float]] = {}
    for snapshot in snapshots:
        if not snapshot.drivers_json:
            continue
        try:
            payload = json.loads(snapshot.drivers_json)
        except json.JSONDecodeError:
            continue
        for key, value in payload.items():
            metrics.setdefault(key, []).append(float(value))

    if not metrics:
        return None

    return {key: sum(values) / len(values) for key, values in metrics.items() if values}


def _build_primary_drivers(
    role_profile: str,
    current_metrics: dict[str, float],
    baseline_metrics: dict[str, float] | None,
) -> list[AIDriverImpact]:
    profile = role_profile or "developer"
    if profile not in {"developer", "manager", "office"}:
        profile = "office"

    driver_defs = {
        "developer": [
            ("context_switches_per_hour", "Контекстные переключения", "lower"),
            ("deep_work_ratio", "Deep work", "higher"),
            ("communication_ratio", "Коммуникации", "lower"),
        ],
        "manager": [
            ("communication_ratio", "Коммуникации", "higher"),
            ("planning_ratio", "Планирование", "higher"),
            ("context_switches_per_hour", "Контекстные переключения", "lower"),
        ],
        "office": [
            ("deep_work_ratio", "Фокусная работа", "higher"),
            ("communication_ratio", "Коммуникации", "higher"),
            ("context_switches_per_hour", "Контекстные переключения", "lower"),
        ],
    }

    drivers: list[AIDriverImpact] = []
    impacts: list[float] = []
    baseline_metrics = baseline_metrics or {}

    for key, title, direction in driver_defs[profile]:
        current_value = float(current_metrics.get(key, 0.0))
        baseline_value = float(baseline_metrics.get(key, 0.0))
        if baseline_value > 0:
            if key.endswith("_ratio"):
                delta = (current_value - baseline_value) / baseline_value
                detail = f"Изменение: {delta * 100:+.0f}% относительно нормы."
            else:
                delta = current_value - baseline_value
                detail = f"Изменение: {delta:+.1f} относительно нормы."
        else:
            delta = 0.0
            if key.endswith("_ratio"):
                detail = f"Текущее значение: {current_value * 100:.0f}%."
            else:
                detail = f"Текущее значение: {current_value:.1f}."

        impact = delta if direction == "higher" else -delta if direction == "lower" else 0.0
        impacts.append(impact)
        drivers.append(
            AIDriverImpact(
                title=title,
                detail=detail,
                impact_pct=impact,
                direction="positive" if impact > 0 else "negative" if impact < 0 else "neutral",
            )
        )

    total = sum(abs(value) for value in impacts)
    if total <= 0:
        for driver in drivers:
            driver.impact_pct = 0.0
        return drivers

    for driver in drivers:
        driver.impact_pct = (driver.impact_pct / total) * 100

    drivers.sort(key=lambda item: abs(item.impact_pct), reverse=True)
    return drivers[:3]


def _trend_summary(points: list[AIScoreTrendPoint]) -> tuple[str, str]:
    if len(points) < 3:
        return "Недостаточно данных для тренда.", "низкая"

    recent = points[-3:]
    earlier = points[:-3]
    recent_avg = sum(point.score for point in recent) / len(recent)
    earlier_avg = sum(point.score for point in earlier) / len(earlier) if earlier else recent_avg
    delta = recent_avg - earlier_avg

    stability = "высокая"
    if abs(delta) >= 8:
        stability = "умеренная"
    if abs(delta) >= 15:
        stability = "низкая"

    if delta >= 8:
        return "Наблюдается устойчивый рост относительно предыдущих периодов.", stability
    if delta <= -8:
        return "Есть устойчивое снижение относительно предыдущих периодов.", stability
    return "Показатели остаются стабильными, без выраженного тренда.", stability


def _build_interpretation(
    scorecard: AIScoreSnapshot,
    baseline: AIScoreBaseline | None,
    drivers: list[AIDriverImpact],
    trend_points: list[AIScoreTrendPoint],
    mode: str,
    team_median_score: float | None,
) -> AIInterpretation:
    score = scorecard.score
    if baseline and baseline.avg_score:
        delta_pct = ((score - baseline.avg_score) / baseline.avg_score) * 100
        vs_baseline = f"{delta_pct:+.0f}% относительно собственной нормы."
        if delta_pct > 0:
            vs_baseline = f"Рост на {abs(delta_pct):.0f}% относительно собственной нормы."
        elif delta_pct < 0:
            vs_baseline = f"Снижение на {abs(delta_pct):.0f}% относительно собственной нормы."
    else:
        delta_pct = None
        vs_baseline = "Недостаточно данных для расчета собственной нормы."

    trend_text, stability = _trend_summary(trend_points)

    summary_lines = [
        f"Текущий score: {score}.",
        vs_baseline,
        trend_text,
    ]

    suggestion = None
    if delta_pct is not None:
        if delta_pct <= -8:
            suggestion = "Опционально: можно сократить параллельные задачи и выделить фокус-блоки в расписании."
        elif delta_pct >= 8:
            suggestion = "Опционально: полезно сохранить текущие практики распределения задач и времени."
        else:
            suggestion = "Опционально: можно продолжать текущий ритм, наблюдая за стабильностью тренда."

    overload_risk = None
    if mode == "executive":
        overload_risk = "не выявлен"
        if delta_pct is not None and delta_pct <= -10:
            negative_focus = any(
                item.title in {"Deep work", "Фокусная работа"} and item.impact_pct < 0 for item in drivers
            )
            if negative_focus:
                overload_risk = "умеренный"

        if team_median_score is not None:
            summary_lines.append(f"Медиана команды: {team_median_score:.0f}.")
        summary_lines.append(f"Стабильность: {stability}.")
        if overload_risk:
            summary_lines.append(f"Риск перегрузки: {overload_risk}.")

    executive_summary = " ".join(summary_lines)

    return AIInterpretation(
        mode=mode,
        executive_summary=executive_summary,
        vs_baseline=vs_baseline,
        primary_drivers=drivers,
        trend=trend_text,
        suggestion=suggestion,
        stability=stability if mode == "executive" else None,
        team_median_score=team_median_score if mode == "executive" else None,
        overload_risk=overload_risk if mode == "executive" else None,
    )


@router.get("/kpi", response_model=AIKPIReport)
def ai_kpi(
    org_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIKPIReport:
    membership = get_org_membership(org_id, current_user, db)

    report = compute_org_kpi_report(
        db,
        org_id,
        start_date=start_date,
        end_date=end_date,
        team_id=team_id,
        project_id=project_id,
    )

    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        report.users = [row for row in report.users if row.user_id == current_user.id]

    active_median = _median([row.active_seconds for row in report.users])
    anomalies: list[AIKPIAnomaly] = []
    user_scores: list[AIKPIUserScore] = []

    for row in report.users:
        score, active_ratio = _score_user(row)

        if row.tasks_total >= 3 and row.completion_rate < 0.3:
            anomalies.append(
                AIKPIAnomaly(
                    code="low_completion",
                    severity="high",
                    title="Низкое завершение задач",
                    detail=f"Выполнено {row.tasks_done} из {row.tasks_total} задач.",
                    user_id=row.user_id,
                )
            )

        if row.observed_seconds >= 3600 and active_ratio < 0.5:
            anomalies.append(
                AIKPIAnomaly(
                    code="low_focus",
                    severity="medium",
                    title="Низкая концентрация",
                    detail="Доля активного времени ниже 50%.",
                    user_id=row.user_id,
                )
            )

        if active_median > 0 and row.active_seconds < active_median * 0.5:
            anomalies.append(
                AIKPIAnomaly(
                    code="low_activity",
                    severity="medium",
                    title="Низкая активность",
                    detail="Активность заметно ниже медианы команды.",
                    user_id=row.user_id,
                )
            )

        user_scores.append(
            AIKPIUserScore(
                user_id=row.user_id,
                full_name=row.full_name,
                sessions_count=row.sessions_count,
                tasks_total=row.tasks_total,
                tasks_done=row.tasks_done,
                completion_rate=row.completion_rate,
                observed_seconds=row.observed_seconds,
                idle_seconds=row.idle_seconds,
                active_seconds=row.active_seconds,
                active_ratio=active_ratio,
                score=score,
            )
        )

    org_score = int(round(sum(item.score for item in user_scores) / len(user_scores))) if user_scores else 0

    return AIKPIReport(
        org_id=org_id,
        start_date=report.start_date,
        end_date=report.end_date,
        team_id=team_id,
        project_id=project_id,
        generated_at=datetime.utcnow(),
        org_score=org_score,
        users=user_scores,
        anomalies=anomalies,
    )


@router.post("/scorecards/rebuild", response_model=AIScoreRebuildResponse)
def rebuild_scorecards(
    org_id: str,
    start_date: date,
    end_date: date,
    period: ScorePeriod = ScorePeriod.daily,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIScoreRebuildResponse:
    membership = get_org_membership(org_id, current_user, db)
    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        raise HTTPException(status_code=403, detail="Not allowed")

    snapshots_count = 0
    periods = _iter_periods(start_date, end_date, period)
    for period_start, period_end in periods:
        report = compute_org_kpi_report(
            db,
            org_id,
            start_date=period_start,
            end_date=period_end,
        )
        for row in report.users:
            _upsert_snapshot(
                db,
                org_id=org_id,
                period_type=period,
                period_start=period_start,
                period_end=period_end,
                user_row=row,
            )
            snapshots_count += 1

    db.commit()
    return AIScoreRebuildResponse(
        org_id=org_id,
        period_type=period.value,
        start_date=start_date,
        end_date=end_date,
        snapshots_count=snapshots_count,
    )


@router.get("/scorecards", response_model=list[AIScorecard])
def scorecards(
    org_id: str,
    period: ScorePeriod = ScorePeriod.daily,
    as_of: date | None = None,
    user_id: str | None = None,
    mode: str = "employee",
    role_profile: str = "developer",
    trend_limit: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIScorecard]:
    membership = get_org_membership(org_id, current_user, db)
    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        user_id = current_user.id

    if as_of is None:
        as_of = date.today()

    mode = mode.strip().lower()
    if mode not in {"employee", "executive"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    period_start, period_end = _period_bounds(as_of, period)
    report = compute_org_kpi_report(
        db,
        org_id,
        start_date=period_start,
        end_date=period_end,
    )

    if user_id:
        report.users = [row for row in report.users if row.user_id == user_id]

    snapshots: dict[str, AIScoreSnapshot] = {}
    for row in report.users:
        snapshots[row.user_id] = _upsert_snapshot(
            db,
            org_id=org_id,
            period_type=period,
            period_start=period_start,
            period_end=period_end,
            user_row=row,
        )

    db.commit()

    scorecards: list[AIScorecard] = []
    team_median_score = None
    if mode == "executive" and report.users:
        scores = [snapshots[row.user_id].score for row in report.users]
        scores_sorted = sorted(scores)
        mid = len(scores_sorted) // 2
        if len(scores_sorted) % 2 == 1:
            team_median_score = float(scores_sorted[mid])
        else:
            team_median_score = (scores_sorted[mid - 1] + scores_sorted[mid]) / 2.0

    for row in report.users:
        snapshot = snapshots[row.user_id]
        baseline = _load_baseline(db, org_id, row.user_id, period, period_start)
        reasons = _build_reasons(snapshot, baseline)
        trend = _load_trend(db, org_id, row.user_id, period, period_start, trend_limit)
        baseline_drivers = _load_driver_baseline(db, org_id, row.user_id, period, period_start)
        current_drivers: dict[str, float] = {}
        if snapshot.drivers_json:
            try:
                current_drivers = json.loads(snapshot.drivers_json)
            except json.JSONDecodeError:
                current_drivers = {}
        drivers = _build_primary_drivers(role_profile, current_drivers, baseline_drivers)
        interpretation = _build_interpretation(
            snapshot,
            baseline,
            drivers,
            trend,
            mode,
            team_median_score,
        )
        delta_score = None
        if baseline:
            delta_score = snapshot.score - baseline.avg_score

        scorecards.append(
            AIScorecard(
                org_id=org_id,
                user_id=row.user_id,
                full_name=row.full_name,
                period_type=period.value,
                period_start=period_start,
                period_end=period_end,
                current=AIScoreSnapshotResponse.model_validate(snapshot),
                baseline=baseline,
                delta_score=delta_score,
                trend=trend,
                reasons=reasons,
                interpretation=interpretation,
            )
        )

    return scorecards
