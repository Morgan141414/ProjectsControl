from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.activity import ActivityEvent, ScreenSession
from app.models.enums import ActivityType, OrgRole, TaskStatus
from app.models.task import Task
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.reports import KPIOrgReport, KPITeamRow, KPIUserRow

router = APIRouter(prefix="/orgs/{org_id}/reports", tags=["reports"])


def _cap_delta(delta_seconds: float) -> int:
    if delta_seconds <= 0:
        return 0
    if delta_seconds > settings.METRICS_MAX_GAP_SECONDS:
        return settings.METRICS_MAX_GAP_SECONDS
    return int(delta_seconds)


def _compute_seconds(events: list[ActivityEvent]) -> tuple[int, int]:
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

    return observed_seconds, idle_seconds


def _load_events(db: Session, session_id: str) -> list[ActivityEvent]:
    return (
        db.query(ActivityEvent)
        .filter(ActivityEvent.session_id == session_id)
        .order_by(ActivityEvent.captured_at.asc())
        .all()
    )


def _apply_date_filter(query, start_date: date | None, end_date: date | None):
    if start_date:
        query = query.filter(ScreenSession.started_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(ScreenSession.started_at <= datetime.combine(end_date, datetime.max.time()))
    return query


def _apply_task_date_filter(query, start_date: date | None, end_date: date | None):
    if start_date:
        query = query.filter(Task.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(Task.created_at <= datetime.combine(end_date, datetime.max.time()))
    return query


def compute_org_kpi_report(
    db: Session,
    org_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
) -> KPIOrgReport:
    sessions_query = (
        db.query(ScreenSession)
        .filter(ScreenSession.org_id == org_id)
        .order_by(ScreenSession.started_at.desc())
    )
    sessions_query = _apply_date_filter(sessions_query, start_date, end_date)
    if team_id:
        sessions_query = (
            sessions_query.join(User, User.id == ScreenSession.user_id)
            .join(TeamMembership, TeamMembership.user_id == User.id)
            .filter(TeamMembership.team_id == team_id)
        )
    if project_id:
        sessions_query = (
            sessions_query.join(User, User.id == ScreenSession.user_id)
            .join(TeamMembership, TeamMembership.user_id == User.id)
            .join(Team, Team.id == TeamMembership.team_id)
            .filter(Team.project_id == project_id)
        )
    sessions = sessions_query.all()

    total_events = 0
    observed_seconds = 0
    idle_seconds = 0
    tasks_total = 0
    tasks_done = 0

    user_rows: dict[str, KPIUserRow] = {}

    for session in sessions:
        events = _load_events(db, session.id)
        session_observed, session_idle = _compute_seconds(events)
        session_events_count = len(events)

        total_events += session_events_count
        observed_seconds += session_observed
        idle_seconds += session_idle

        row = user_rows.get(session.user_id)
        if not row:
            user = db.get(User, session.user_id)
            full_name = user.full_name if user else session.user_id
            row = KPIUserRow(
                user_id=session.user_id,
                full_name=full_name,
                sessions_count=0,
                total_events=0,
                observed_seconds=0,
                idle_seconds=0,
                active_seconds=0,
                tasks_total=0,
                tasks_done=0,
                completion_rate=0.0,
            )
            user_rows[session.user_id] = row

        row.sessions_count += 1
        row.total_events += session_events_count
        row.observed_seconds += session_observed
        row.idle_seconds += session_idle
        row.active_seconds = max(row.observed_seconds - row.idle_seconds, 0)

    tasks_query = db.query(Task).filter(Task.org_id == org_id, Task.assignee_id.isnot(None))
    tasks_query = _apply_task_date_filter(tasks_query, start_date, end_date)
    if team_id:
        tasks_query = tasks_query.filter(Task.team_id == team_id)
    if project_id:
        tasks_query = tasks_query.join(Team, Team.id == Task.team_id).filter(Team.project_id == project_id)
    tasks = tasks_query.all()

    for task in tasks:
        row = user_rows.get(task.assignee_id)
        if not row:
            user = db.get(User, task.assignee_id)
            full_name = user.full_name if user else task.assignee_id
            row = KPIUserRow(
                user_id=task.assignee_id,
                full_name=full_name,
                sessions_count=0,
                total_events=0,
                observed_seconds=0,
                idle_seconds=0,
                active_seconds=0,
                tasks_total=0,
                tasks_done=0,
                completion_rate=0.0,
            )
            user_rows[task.assignee_id] = row

        row.tasks_total += 1
        if task.status == TaskStatus.done:
            row.tasks_done += 1

    for row in user_rows.values():
        if row.tasks_total:
            row.completion_rate = row.tasks_done / row.tasks_total

    users = sorted(user_rows.values(), key=lambda item: item.active_seconds, reverse=True)

    team_rows: dict[str, KPITeamRow] = {}
    teams_query = db.query(Team).filter(Team.org_id == org_id)
    if team_id:
        teams_query = teams_query.filter(Team.id == team_id)
    if project_id:
        teams_query = teams_query.filter(Team.project_id == project_id)
    teams = teams_query.all()
    for team in teams:
        team_rows[team.id] = KPITeamRow(
            team_id=team.id,
            team_name=team.name,
            users_count=0,
            sessions_count=0,
            total_events=0,
            observed_seconds=0,
            idle_seconds=0,
            active_seconds=0,
            tasks_total=0,
            tasks_done=0,
            completion_rate=0.0,
        )

    team_members_query = (
        db.query(TeamMembership)
        .join(Team, TeamMembership.team_id == Team.id)
        .filter(Team.org_id == org_id)
    )
    if team_id:
        team_members_query = team_members_query.filter(TeamMembership.team_id == team_id)
    if project_id:
        team_members_query = team_members_query.filter(Team.project_id == project_id)
    team_members = team_members_query.all()
    team_map: dict[str, list[str]] = {}
    for membership_row in team_members:
        team_map.setdefault(membership_row.team_id, []).append(membership_row.user_id)

    for team_id, team_row in team_rows.items():
        users_in_team = set(team_map.get(team_id, []))
        team_row.users_count = len(users_in_team)
        for user_id in users_in_team:
            user_row = user_rows.get(user_id)
            if not user_row:
                continue
            team_row.sessions_count += user_row.sessions_count
            team_row.total_events += user_row.total_events
            team_row.observed_seconds += user_row.observed_seconds
            team_row.idle_seconds += user_row.idle_seconds
            team_row.tasks_total += user_row.tasks_total
            team_row.tasks_done += user_row.tasks_done
        team_row.active_seconds = max(team_row.observed_seconds - team_row.idle_seconds, 0)
        if team_row.tasks_total:
            team_row.completion_rate = team_row.tasks_done / team_row.tasks_total

    teams_report = sorted(team_rows.values(), key=lambda item: item.active_seconds, reverse=True)

    total_users = len(user_rows)
    total_sessions = len(sessions)
    active_seconds = max(observed_seconds - idle_seconds, 0)
    tasks_total = sum(row.tasks_total for row in user_rows.values())
    tasks_done = sum(row.tasks_done for row in user_rows.values())
    completion_rate = (tasks_done / tasks_total) if tasks_total else 0.0

    return KPIOrgReport(
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        total_users=total_users,
        total_sessions=total_sessions,
        total_events=total_events,
        observed_seconds=observed_seconds,
        idle_seconds=idle_seconds,
        active_seconds=active_seconds,
        tasks_total=tasks_total,
        tasks_done=tasks_done,
        completion_rate=completion_rate,
        users=users,
        teams=teams_report,
    )


@router.get("/kpi", response_model=KPIOrgReport)
def kpi_report(
    org_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KPIOrgReport:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return compute_org_kpi_report(
        db,
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        team_id=team_id,
        project_id=project_id,
    )
