from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.enums import AuditAction, OrgRole
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])


def _project_visibility_query(org_id: str, db: Session, current_user: User):
    membership = get_org_membership(org_id, current_user, db)
    if membership.role in {OrgRole.admin, OrgRole.manager}:
        return db.query(Project).filter(Project.org_id == org_id)

    team_ids = (
        db.query(TeamMembership.team_id)
        .join(Team, TeamMembership.team_id == Team.id)
        .filter(TeamMembership.user_id == current_user.id, Team.org_id == org_id)
        .all()
    )
    team_ids = [row[0] for row in team_ids]
    if not team_ids:
        return db.query(Project).filter(Project.id == "__none__")

    return db.query(Project).join(Team, Team.project_id == Project.id).filter(Team.id.in_(team_ids))


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    org_id: str,
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    project = Project(org_id=org_id, name=payload.name, description=payload.description)
    db.add(project)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="project",
        entity_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    return _project_visibility_query(org_id, db, current_user).order_by(Project.name).all()


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    org_id: str,
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = (
        _project_visibility_query(org_id, db, current_user)
        .filter(Project.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    org_id: str,
    project_id: str,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    project = db.get(Project, project_id)
    if not project or project.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="project",
        entity_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project
