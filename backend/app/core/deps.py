from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import SessionLocal
from app.models.enums import OrgRole
from app.models.org import OrgMembership
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_superadmin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return user


def get_org_membership(
    org_id: str,
    user: User,
    db: Session,
) -> OrgMembership:
    membership = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == user.id)
        .first()
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization",
        )
    return membership


def require_role(membership: OrgMembership, allowed_roles: set[OrgRole]) -> None:
    if membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )


def check_tariff_limit(org_id: str, resource: str, db: Session) -> None:
    """Check if organization has exceeded its tariff plan limit."""
    from app.models.tariff import Subscription, TariffPlan
    from app.models.org import Organization

    sub = (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id, Subscription.status == "active")
        .first()
    )
    if not sub:
        return  # No subscription = no limits (free tier)

    plan = db.get(TariffPlan, sub.tariff_plan_id)
    if not plan:
        return

    limits = {
        "employees": plan.max_employees,
        "teams": plan.max_teams,
        "projects": plan.max_projects,
    }

    limit_val = limits.get(resource)
    if not limit_val:
        return

    from app.models.org import OrgMembership
    from app.models.team import Team
    from app.models.project import Project

    counts = {
        "employees": db.query(OrgMembership).filter(OrgMembership.org_id == org_id).count(),
        "teams": db.query(Team).filter(Team.org_id == org_id).count(),
        "projects": db.query(Project).filter(Project.org_id == org_id).count(),
    }

    if counts.get(resource, 0) >= limit_val:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tariff limit reached for {resource}. Current: {counts[resource]}, Limit: {limit_val}",
        )
