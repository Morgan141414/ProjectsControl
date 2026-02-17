"""Tariff plans and subscription routes."""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_org_membership, require_role
from app.core.time import utc_now_naive
from app.models.enums import OrgRole, SubscriptionStatus
from app.models.tariff import Subscription, TariffPlan
from app.models.user import User
from app.schemas.tariff import SubscriptionOut, TariffPlanOut

router = APIRouter(tags=["tariffs"])


@router.get("/tariffs", response_model=list[TariffPlanOut])
def list_tariffs(db: Session = Depends(get_db)):
    return db.query(TariffPlan).filter(TariffPlan.is_active == True).all()


@router.get("/tariffs/{tariff_id}", response_model=TariffPlanOut)
def get_tariff(tariff_id: str, db: Session = Depends(get_db)):
    plan = db.get(TariffPlan, tariff_id)
    if not plan:
        raise HTTPException(404, "Tariff plan not found")
    return plan


@router.get("/orgs/{org_id}/subscription")
def get_subscription(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_org_membership(org_id, user, db)
    sub = (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id, Subscription.status == SubscriptionStatus.active)
        .first()
    )
    if not sub:
        return None
    return SubscriptionOut.model_validate(sub)


@router.post("/orgs/{org_id}/subscription/upgrade")
def upgrade_subscription(
    org_id: str,
    tariff_code: str,
    billing: str = "monthly",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    plan = db.query(TariffPlan).filter(TariffPlan.code == tariff_code, TariffPlan.is_active == True).first()
    if not plan:
        raise HTTPException(404, "Tariff plan not found")

    current = (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id, Subscription.status == SubscriptionStatus.active)
        .first()
    )
    if current:
        current.status = SubscriptionStatus.cancelled

    now = utc_now_naive()
    days = 365 if billing == "yearly" else 30
    sub = Subscription(
        org_id=org_id,
        tariff_plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=days),
    )
    db.add(sub)
    db.commit()
    return {"subscription_id": sub.id, "tariff": plan.code, "ends_at": sub.ends_at.isoformat()}


@router.post("/orgs/{org_id}/subscription/cancel")
def cancel_subscription(
    org_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    sub = (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id, Subscription.status == SubscriptionStatus.active)
        .first()
    )
    if not sub:
        raise HTTPException(404, "No active subscription")
    sub.status = SubscriptionStatus.cancelled
    sub.auto_renew = False
    db.commit()
    return {"status": "cancelled"}


@router.post("/orgs/{org_id}/subscription/renew")
def renew_subscription(
    org_id: str,
    billing: str = "monthly",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    sub = (
        db.query(Subscription)
        .filter(Subscription.org_id == org_id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if not sub:
        raise HTTPException(404, "No subscription found")

    now = utc_now_naive()
    base = sub.ends_at if sub.ends_at > now else now
    days = 365 if billing == "yearly" else 30
    sub.ends_at = base + timedelta(days=days)
    sub.status = SubscriptionStatus.active
    sub.auto_renew = True
    db.commit()
    return {"status": "renewed", "ends_at": sub.ends_at.isoformat()}
