from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.enums import AuditAction, OrgRole, TeamRole
from app.models.org import OrgMembership
from app.models.project import Project
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamResponse, TeamUpdate

router = APIRouter(prefix="/orgs/{org_id}/teams", tags=["teams"])


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    org_id: str,
    payload: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Team:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    project_id = None
    if payload.project_id:
        project = db.get(Project, payload.project_id)
        if not project or project.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project")
        project_id = payload.project_id

    team = Team(org_id=org_id, name=payload.name, project_id=project_id)
    db.add(team)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="team",
        entity_id=team.id,
    )
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=list[TeamResponse])
def list_teams(
    org_id: str,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Team]:
    get_org_membership(org_id, current_user, db)
    query = db.query(Team).filter(Team.org_id == org_id)
    if project_id:
        query = query.filter(Team.project_id == project_id)
    return query.order_by(Team.name).all()


@router.get("/me", response_model=list[TeamResponse])
def list_my_teams(
    org_id: str,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Team]:
    get_org_membership(org_id, current_user, db)
    query = (
        db.query(Team)
        .join(TeamMembership, TeamMembership.team_id == Team.id)
        .filter(TeamMembership.user_id == current_user.id, Team.org_id == org_id)
    )
    if project_id:
        query = query.filter(Team.project_id == project_id)
    return query.order_by(Team.name).all()


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    org_id: str,
    team_id: str,
    payload: TeamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Team:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    team = db.get(Team, team_id)
    if not team or team.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    if payload.name is not None:
        team.name = payload.name
    if payload.project_id is not None:
        if payload.project_id == "":
            team.project_id = None
        else:
            project = db.get(Project, payload.project_id)
            if not project or project.org_id != org_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid project")
            team.project_id = payload.project_id

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="team",
        entity_id=team.id,
    )
    db.commit()
    db.refresh(team)
    return team


@router.post("/{team_id}/members", response_model=TeamResponse)
def add_team_member(
    org_id: str,
    team_id: str,
    payload: TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Team:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    team = db.get(Team, team_id)
    if not team or team.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

    target_membership = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == payload.user_id)
        .first()
    )
    if not target_membership:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not in org")

    existing = (
        db.query(TeamMembership)
        .filter(TeamMembership.team_id == team_id, TeamMembership.user_id == payload.user_id)
        .first()
    )
    if not existing:
        role = payload.role or TeamRole.member
        db.add(TeamMembership(team_id=team_id, user_id=payload.user_id, role=role))
        log_audit(
            db,
            org_id=org_id,
            actor_id=current_user.id,
            action=AuditAction.update,
            entity_type="team_member",
            entity_id=team_id,
            details=f"user_id={payload.user_id}",
        )
        db.commit()

    db.refresh(team)
    return team
