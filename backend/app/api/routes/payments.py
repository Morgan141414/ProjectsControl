"""Payment and ban system routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, require_superadmin
from app.models.payment import BanAppeal, Payment, UserBan
from app.models.user import User
from app.schemas.payment import BanAppealCreate, BanAppealOut, BanOut, PaymentOut

router = APIRouter(tags=["payments"])


@router.get("/users/me/payments")
def my_payments(
    skip: int = 0,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Payment).filter(Payment.user_id == user.id)
    total = q.count()
    payments = q.order_by(Payment.created_at.desc()).offset(skip).limit(limit).all()
    return {"items": [PaymentOut.model_validate(p) for p in payments], "total": total}


@router.get("/users/me/bans")
def my_bans(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bans = (
        db.query(UserBan)
        .filter(UserBan.user_id == user.id, UserBan.is_active == True)
        .all()
    )
    return [BanOut.model_validate(b) for b in bans]


@router.post("/bans/{ban_id}/appeal", response_model=BanAppealOut)
def create_appeal(
    ban_id: str,
    body: BanAppealCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ban = db.get(UserBan, ban_id)
    if not ban or ban.user_id != user.id:
        raise HTTPException(404, "Ban not found")

    existing = (
        db.query(BanAppeal)
        .filter(BanAppeal.ban_id == ban_id, BanAppeal.status == "pending")
        .first()
    )
    if existing:
        raise HTTPException(409, "Appeal already pending")

    appeal = BanAppeal(
        ban_id=ban_id,
        user_id=user.id,
        reason=body.reason,
        payment_option=body.payment_option,
    )
    db.add(appeal)
    db.commit()
    db.refresh(appeal)
    return appeal


@router.get("/admin/ban-appeals")
def list_appeals(
    status: str | None = None,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    q = db.query(BanAppeal)
    if status:
        q = q.filter(BanAppeal.status == status)
    appeals = q.order_by(BanAppeal.created_at.desc()).all()
    return [BanAppealOut.model_validate(a) for a in appeals]


@router.post("/admin/ban-appeals/{appeal_id}/approve")
def approve_appeal(
    appeal_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    appeal = db.get(BanAppeal, appeal_id)
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    appeal.status = "approved"
    appeal.reviewed_by = admin.id

    ban = db.get(UserBan, appeal.ban_id)
    if ban:
        ban.is_active = False
        target = db.get(User, ban.user_id)
        if target:
            target.is_active = True
    db.commit()
    return {"status": "approved"}


@router.post("/admin/ban-appeals/{appeal_id}/reject")
def reject_appeal(
    appeal_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    appeal = db.get(BanAppeal, appeal_id)
    if not appeal:
        raise HTTPException(404, "Appeal not found")
    appeal.status = "rejected"
    appeal.reviewed_by = admin.id
    db.commit()
    return {"status": "rejected"}
