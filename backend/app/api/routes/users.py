from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/orgs/{org_id}/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def list_users(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[User]:
    get_org_membership(org_id, current_user, db)

    team_ids = (
        db.query(TeamMembership.team_id)
        .join(Team, TeamMembership.team_id == Team.id)
        .filter(TeamMembership.user_id == current_user.id, Team.org_id == org_id)
        .all()
    )
    team_ids = [row[0] for row in team_ids]

    if not team_ids:
        return [current_user]

    user_ids = (
        db.query(TeamMembership.user_id)
        .filter(TeamMembership.team_id.in_(team_ids))
        .distinct()
        .all()
    )
    user_ids = [row[0] for row in user_ids]

    return db.query(User).filter(User.id.in_(user_ids)).order_by(User.full_name).all()
