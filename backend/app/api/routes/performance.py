from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.activity import ActivityEvent, ScreenSession
from app.models.enums import ActivityType, OrgRole, TaskStatus
from app.models.project import Project
from app.models.task import Task
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.performance import ActivityPerTaskResponse

router = APIRouter(prefix="/orgs/{org_id}/performance", tags=["performance"])


def _require_manager_or_self(current_user: User, target_user_id: str, role: OrgRole) -> None:
    if current_user.id != target_user_id and role not in {OrgRole.admin, OrgRole.manager}:
        raise HTTPException(status_code=403, detail="Not allowed")


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


def _compute_seconds(events: list[ActivityEvent]) -> tuple[int, int]:
    observed_seconds = 0
    idle_seconds = 0

    for index in range(len(events) - 1):
        current = events[index]
        next_event = events[index + 1]
        delta_seconds = (next_event.captured_at - current.captured_at).total_seconds()
        if delta_seconds <= 0:
            continue
        observed_seconds += int(delta_seconds)

        if current.event_type == ActivityType.idle:
            if current.idle_seconds is not None:
                idle_seconds += min(current.idle_seconds, int(delta_seconds))
            else:
                idle_seconds += int(delta_seconds)

    return observed_seconds, idle_seconds


@router.get("/activity-per-task", response_model=ActivityPerTaskResponse)
def activity_per_task(
    org_id: str,
    user_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityPerTaskResponse:
    membership = get_org_membership(org_id, current_user, db)
    _require_manager_or_self(current_user, user_id, membership.role)

    team = None
    if team_id:
        team = db.get(Team, team_id)
        if not team or team.org_id != org_id:
            raise HTTPException(status_code=404, detail="Team not found")
        is_member = (
            db.query(TeamMembership)
            .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == user_id)
            .first()
        )
        if not is_member:
            raise HTTPException(status_code=404, detail="User not in team")

    if project_id:
        project = db.get(Project, project_id)
        if not project or project.org_id != org_id:
            raise HTTPException(status_code=404, detail="Project not found")
        if team and team.project_id != project_id:
            raise HTTPException(status_code=400, detail="Team not in project")
        is_member = (
            db.query(TeamMembership)
            .join(Team, TeamMembership.team_id == Team.id)
            .filter(TeamMembership.user_id == user_id, Team.project_id == project_id)
            .first()
        )
        if not is_member:
            raise HTTPException(status_code=404, detail="User not in project")

    sessions_query = db.query(ScreenSession).filter(
        ScreenSession.org_id == org_id,
        ScreenSession.user_id == user_id,
    )
    sessions_query = _apply_date_filter(sessions_query, start_date, end_date)
    sessions = sessions_query.all()

    observed_seconds = 0
    idle_seconds = 0
    for session in sessions:
        events = _load_events(db, session.id)
        session_observed, session_idle = _compute_seconds(events)
        observed_seconds += session_observed
        idle_seconds += session_idle

    tasks_query = db.query(Task).filter(Task.org_id == org_id, Task.assignee_id == user_id)
    tasks_query = _apply_task_date_filter(tasks_query, start_date, end_date)
    if team_id:
        tasks_query = tasks_query.filter(Task.team_id == team_id)
    if project_id:
        tasks_query = tasks_query.join(Team, Team.id == Task.team_id).filter(Team.project_id == project_id)
    tasks = tasks_query.all()

    tasks_total = len(tasks)
    tasks_done = sum(1 for task in tasks if task.status == TaskStatus.done)
    active_seconds = max(observed_seconds - idle_seconds, 0)

    seconds_per_task = (observed_seconds / tasks_total) if tasks_total else 0.0
    active_seconds_per_task = (active_seconds / tasks_total) if tasks_total else 0.0

    return ActivityPerTaskResponse(
        org_id=org_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        team_id=team_id,
        project_id=project_id,
        tasks_total=tasks_total,
        tasks_done=tasks_done,
        observed_seconds=observed_seconds,
        active_seconds=active_seconds,
        seconds_per_task=seconds_per_task,
        active_seconds_per_task=active_seconds_per_task,
    )
