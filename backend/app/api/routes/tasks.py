from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.enums import AuditAction, OrgRole
from app.models.org import OrgMembership
from app.models.task import Task
from app.models.team import Team
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/orgs/{org_id}/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    org_id: str,
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    if payload.assignee_id:
        assignee_membership = (
            db.query(OrgMembership)
            .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == payload.assignee_id)
            .first()
        )
        if not assignee_membership:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee not in org")

    if payload.team_id:
        team = db.get(Team, payload.team_id)
        if not team or team.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid team")

    task = Task(
        org_id=org_id,
        team_id=payload.team_id,
        assignee_id=payload.assignee_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
    )
    db.add(task)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="task",
        entity_id=task.id,
    )
    db.commit()
    db.refresh(task)
    return task


@router.get("/today", response_model=list[TaskResponse])
def list_today_tasks(
    org_id: str,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Task]:
    get_org_membership(org_id, current_user, db)
    today = date.today()

    query = (
        db.query(Task)
        .filter(
            Task.org_id == org_id,
            Task.assignee_id == current_user.id,
            Task.due_date == today,
        )
    )
    if project_id:
        query = query.join(Team, Team.id == Task.team_id).filter(Team.project_id == project_id)
    return query.order_by(Task.created_at.desc()).all()


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    org_id: str,
    task_id: str,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    membership = get_org_membership(org_id, current_user, db)
    task = db.get(Task, task_id)
    if not task or task.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    if task.assignee_id != current_user.id and membership.role not in {
        OrgRole.admin,
        OrgRole.manager,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    if payload.status is not None:
        task.status = payload.status
    if payload.report is not None:
        task.report = payload.report

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="task",
        entity_id=task.id,
    )
    db.commit()
    db.refresh(task)
    return task
