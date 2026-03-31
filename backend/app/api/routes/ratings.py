"""Rating system routes."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_org_membership, require_role, require_superadmin
from app.models.enums import OrgRole, RatingTrend
from app.models.rating import EmployeeMonthlyRating, EmployeePublicRating, OrgPublicRating
from app.models.user import User
from app.schemas.rating import EmployeeMonthlyRatingOut, EmployeePublicRatingOut, OrgPublicRatingOut

router = APIRouter(tags=["ratings"])


@router.get("/ratings/employees/public")
def list_public_employee_ratings(
    quarter: str | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(EmployeePublicRating).filter(EmployeePublicRating.is_published == True)
    if quarter:
        q = q.filter(EmployeePublicRating.quarter == quarter)
    if year:
        q = q.filter(EmployeePublicRating.year == year)
    total = q.count()
    ratings = q.order_by(EmployeePublicRating.overall_score.desc()).offset(skip).limit(limit).all()
    return {"items": [EmployeePublicRatingOut.model_validate(r) for r in ratings], "total": total}


@router.get("/ratings/employees/{user_id}/public")
def get_employee_public_rating(
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ratings = (
        db.query(EmployeePublicRating)
        .filter(EmployeePublicRating.user_id == user_id, EmployeePublicRating.is_published == True)
        .order_by(EmployeePublicRating.year.desc(), EmployeePublicRating.quarter.desc())
        .all()
    )
    return [EmployeePublicRatingOut.model_validate(r) for r in ratings]


@router.get("/ratings/orgs/public")
def list_public_org_ratings(
    quarter: str | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(OrgPublicRating).filter(OrgPublicRating.is_published == True)
    if quarter:
        q = q.filter(OrgPublicRating.quarter == quarter)
    if year:
        q = q.filter(OrgPublicRating.year == year)
    total = q.count()
    ratings = q.order_by(OrgPublicRating.overall_score.desc()).offset(skip).limit(limit).all()
    return {"items": [OrgPublicRatingOut.model_validate(r) for r in ratings], "total": total}


@router.get("/orgs/{org_id}/ratings/monthly")
def list_monthly_ratings(
    org_id: str,
    month: int | None = None,
    year: int | None = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.manager})

    q = db.query(EmployeeMonthlyRating).filter(EmployeeMonthlyRating.org_id == org_id)
    if month:
        q = q.filter(EmployeeMonthlyRating.month == month)
    if year:
        q = q.filter(EmployeeMonthlyRating.year == year)
    total = q.count()
    ratings = q.order_by(EmployeeMonthlyRating.overall_score.desc()).offset(skip).limit(limit).all()
    return {"items": [EmployeeMonthlyRatingOut.model_validate(r) for r in ratings], "total": total}


@router.get("/orgs/{org_id}/ratings/monthly/{user_id}")
def get_monthly_rating(
    org_id: str,
    user_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    if user.id != user_id:
        require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.manager})

    ratings = (
        db.query(EmployeeMonthlyRating)
        .filter(EmployeeMonthlyRating.org_id == org_id, EmployeeMonthlyRating.user_id == user_id)
        .order_by(EmployeeMonthlyRating.year.desc(), EmployeeMonthlyRating.month.desc())
        .limit(12)
        .all()
    )
    return [EmployeeMonthlyRatingOut.model_validate(r) for r in ratings]


@router.get("/orgs/{org_id}/ratings/leaderboard")
def org_leaderboard(
    org_id: str,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    now = datetime.utcnow()

    ratings = (
        db.query(EmployeeMonthlyRating)
        .filter(
            EmployeeMonthlyRating.org_id == org_id,
            EmployeeMonthlyRating.year == now.year,
            EmployeeMonthlyRating.month == now.month,
        )
        .order_by(EmployeeMonthlyRating.overall_score.desc())
        .limit(limit)
        .all()
    )

    result = []
    for i, r in enumerate(ratings, 1):
        u = db.get(User, r.user_id)
        result.append({
            "rank": i,
            "user_id": r.user_id,
            "full_name": u.full_name if u else "Unknown",
            "avatar_url": u.avatar_url if u else None,
            "overall_score": r.overall_score,
            "trend": r.trend.value if isinstance(r.trend, RatingTrend) else r.trend,
            "tasks_completed": r.tasks_completed,
        })
    return result


@router.post("/admin/ratings/recalculate")
def recalculate_ratings(
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    return {"status": "recalculation_queued", "message": "Rating recalculation has been queued"}
