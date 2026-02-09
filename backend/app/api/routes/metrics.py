from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.activity import ActivityEvent, ScreenSession
from app.models.enums import ActivityType, OrgRole
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.metrics import AppUsageItem, SessionMetricsResponse, UserMetricsResponse

router = APIRouter(prefix="/orgs/{org_id}/metrics", tags=["metrics"])


def _cap_delta(delta_seconds: float) -> int:
    if delta_seconds <= 0:
        return 0
    if delta_seconds > settings.METRICS_MAX_GAP_SECONDS:
        return settings.METRICS_MAX_GAP_SECONDS
    return int(delta_seconds)


def _compute_usage(events: list[ActivityEvent]) -> tuple[int, int, list[AppUsageItem]]:
    usage: dict[str, AppUsageItem] = {}
    observed_seconds = 0
    idle_seconds = 0

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
            continue

        if not current.app_name:
            continue

        item = usage.get(current.app_name)
        if not item:
            item = AppUsageItem(app_name=current.app_name, seconds=0, events=0)
            usage[current.app_name] = item
        item.seconds += delta
        item.events += 1

    app_usage = sorted(usage.values(), key=lambda item: item.seconds, reverse=True)
    return observed_seconds, idle_seconds, app_usage


def _load_events(db: Session, session_id: str) -> list[ActivityEvent]:
    return (
        db.query(ActivityEvent)
        .filter(ActivityEvent.session_id == session_id)
        .order_by(ActivityEvent.captured_at.asc())
        .all()
    )


def _require_manager_or_self(current_user: User, target_user_id: str, role: OrgRole) -> None:
    if current_user.id != target_user_id and role not in {OrgRole.admin, OrgRole.manager}:
        raise HTTPException(status_code=403, detail="Not allowed")


@router.get("/sessions/{session_id}", response_model=SessionMetricsResponse)
def session_metrics(
    org_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionMetricsResponse:
    membership = get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=404, detail="Session not found")

    _require_manager_or_self(current_user, session.user_id, membership.role)

    events = _load_events(db, session_id)
    observed_seconds, idle_seconds, app_usage = _compute_usage(events)
    active_seconds = max(observed_seconds - idle_seconds, 0)

    return SessionMetricsResponse(
        session_id=session.id,
        org_id=org_id,
        user_id=session.user_id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        total_events=len(events),
        observed_seconds=observed_seconds,
        idle_seconds=idle_seconds,
        active_seconds=active_seconds,
        app_usage=app_usage,
    )


@router.get("/users/{user_id}", response_model=UserMetricsResponse)
def user_metrics(
    org_id: str,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserMetricsResponse:
    membership = get_org_membership(org_id, current_user, db)
    _require_manager_or_self(current_user, user_id, membership.role)

    if project_id:
        project = db.get(Project, project_id)
        if not project or project.org_id != org_id:
            raise HTTPException(status_code=404, detail="Project not found")

        team_user = (
            db.query(TeamMembership)
            .join(Team, TeamMembership.team_id == Team.id)
            .filter(TeamMembership.user_id == user_id, Team.project_id == project_id)
            .first()
        )
        if not team_user:
            raise HTTPException(status_code=404, detail="User not in project")

    query = db.query(ScreenSession).filter(
        ScreenSession.org_id == org_id,
        ScreenSession.user_id == user_id,
    )
    if start_date:
        query = query.filter(ScreenSession.started_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(ScreenSession.started_at <= datetime.combine(end_date, datetime.max.time()))

    sessions = query.order_by(ScreenSession.started_at.desc()).all()

    total_events = 0
    observed_seconds = 0
    idle_seconds = 0
    app_usage: dict[str, AppUsageItem] = {}

    for session in sessions:
        events = _load_events(db, session.id)
        session_observed, session_idle, session_apps = _compute_usage(events)
        total_events += len(events)
        observed_seconds += session_observed
        idle_seconds += session_idle

        for item in session_apps:
            existing = app_usage.get(item.app_name)
            if not existing:
                app_usage[item.app_name] = AppUsageItem(
                    app_name=item.app_name, seconds=item.seconds, events=item.events
                )
            else:
                existing.seconds += item.seconds
                existing.events += item.events

    active_seconds = max(observed_seconds - idle_seconds, 0)
    app_usage_list = sorted(app_usage.values(), key=lambda item: item.seconds, reverse=True)

    return UserMetricsResponse(
        org_id=org_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        sessions_count=len(sessions),
        total_events=total_events,
        observed_seconds=observed_seconds,
        idle_seconds=idle_seconds,
        active_seconds=active_seconds,
        app_usage=app_usage_list,
    )
