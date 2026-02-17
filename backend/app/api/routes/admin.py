"""Superadmin routes for platform management."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_superadmin
from app.core.time import utc_now_naive
from app.models.certificate import OrganizationCertificate
from app.models.enums import CertificateStatus, OrgRole
from app.models.org import OrgMembership, Organization
from app.models.payment import UserBan
from app.models.tariff import Subscription, TariffPlan
from app.models.user import User
from app.schemas.certificate import CertificateCreate, CertificateOut, CertificateRenew

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Organization management ─────────────────────────────────────

@router.get("/orgs")
def list_all_orgs(
    skip: int = 0,
    limit: int = 50,
    status: str | None = None,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    q = db.query(Organization)
    if status == "active":
        q = q.filter(Organization.is_active == True)
    elif status == "suspended":
        q = q.filter(Organization.is_active == False)
    orgs = q.offset(skip).limit(limit).all()
    total = q.count()
    results = []
    for org in orgs:
        member_count = db.query(OrgMembership).filter(OrgMembership.org_id == org.id).count()
        cert = (
            db.query(OrganizationCertificate)
            .filter(OrganizationCertificate.org_id == org.id)
            .first()
        )
        results.append({
            "id": org.id,
            "name": org.name,
            "join_code": org.join_code,
            "description": org.description,
            "industry": org.industry,
            "is_active": org.is_active,
            "owner_id": org.owner_id,
            "member_count": member_count,
            "certificate_status": cert.status.value if cert else None,
            "created_at": org.created_at.isoformat() if org.created_at else None,
        })
    return {"items": results, "total": total}


@router.post("/orgs")
def create_org_as_superadmin(
    name: str,
    owner_id: str,
    industry: str | None = None,
    description: str | None = None,
    valid_months: int = 12,
    max_employees: int = 50,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    owner = db.get(User, owner_id)
    if not owner:
        raise HTTPException(404, "Owner user not found")

    org = Organization(
        name=name,
        owner_id=owner_id,
        industry=industry,
        description=description,
        max_members=max_employees,
        is_active=True,
    )
    db.add(org)
    db.flush()

    # Add owner as admin member
    membership = OrgMembership(
        org_id=org.id,
        user_id=owner_id,
        role=OrgRole.owner,
    )
    db.add(membership)

    # Create certificate
    now = utc_now_naive()
    cert = OrganizationCertificate(
        org_id=org.id,
        issued_at=now,
        valid_from=now,
        valid_until=now + timedelta(days=valid_months * 30),
        owner_id=owner_id,
        issued_by_id=admin.id,
        industry=industry,
        max_employees=max_employees,
    )
    db.add(cert)
    db.commit()

    return {
        "org_id": org.id,
        "certificate_number": cert.certificate_number,
        "join_code": org.join_code,
    }


@router.post("/orgs/{org_id}/suspend")
def suspend_org(
    org_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    org.is_active = False
    org.suspended_at = utc_now_naive()

    cert = (
        db.query(OrganizationCertificate)
        .filter(OrganizationCertificate.org_id == org_id, OrganizationCertificate.status == CertificateStatus.active)
        .first()
    )
    if cert:
        cert.status = CertificateStatus.suspended
    db.commit()
    return {"status": "suspended"}


@router.post("/orgs/{org_id}/activate")
def activate_org(
    org_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    org = db.get(Organization, org_id)
    if not org:
        raise HTTPException(404, "Organization not found")
    org.is_active = True
    org.suspended_at = None

    cert = (
        db.query(OrganizationCertificate)
        .filter(OrganizationCertificate.org_id == org_id, OrganizationCertificate.status == CertificateStatus.suspended)
        .first()
    )
    if cert:
        cert.status = CertificateStatus.active
    db.commit()
    return {"status": "active"}


# ── Certificate management ───────────────────────────────────────

@router.get("/orgs/{org_id}/certificate", response_model=CertificateOut)
def get_certificate(
    org_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    cert = (
        db.query(OrganizationCertificate)
        .filter(OrganizationCertificate.org_id == org_id)
        .order_by(OrganizationCertificate.created_at.desc())
        .first()
    )
    if not cert:
        raise HTTPException(404, "Certificate not found")
    return cert


@router.post("/orgs/{org_id}/certificate/renew")
def renew_certificate(
    org_id: str,
    body: CertificateRenew,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    cert = (
        db.query(OrganizationCertificate)
        .filter(OrganizationCertificate.org_id == org_id)
        .order_by(OrganizationCertificate.created_at.desc())
        .first()
    )
    if not cert:
        raise HTTPException(404, "Certificate not found")

    now = utc_now_naive()
    base = cert.valid_until if cert.valid_until > now else now
    cert.valid_until = base + timedelta(days=body.months * 30)
    cert.status = CertificateStatus.active
    db.commit()
    return {"certificate_number": cert.certificate_number, "valid_until": cert.valid_until.isoformat()}


@router.post("/orgs/{org_id}/certificate/revoke")
def revoke_certificate(
    org_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    cert = (
        db.query(OrganizationCertificate)
        .filter(OrganizationCertificate.org_id == org_id, OrganizationCertificate.status != CertificateStatus.revoked)
        .first()
    )
    if not cert:
        raise HTTPException(404, "Active certificate not found")
    cert.status = CertificateStatus.revoked
    db.commit()
    return {"status": "revoked"}


# ── User management ─────────────────────────────────────────────

@router.get("/users")
def list_all_users(
    skip: int = 0,
    limit: int = 50,
    q: str | None = None,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    query = db.query(User)
    if q:
        query = query.filter(
            (User.full_name.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
        )
    total = query.count()
    users = query.offset(skip).limit(limit).all()
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "is_superadmin": u.is_superadmin,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
    }


@router.post("/users/{user_id}/make-superadmin")
def make_superadmin(
    user_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_superadmin = True
    db.commit()
    return {"status": "ok", "user_id": user_id}


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: str,
    reason: str = "Policy violation",
    ban_type: str = "temporary",
    days: int = 7,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    now = utc_now_naive()
    ban = UserBan(
        user_id=user_id,
        reason=reason,
        banned_by=admin.id,
        ban_type=ban_type,
        starts_at=now,
        ends_at=now + timedelta(days=days) if ban_type == "temporary" else None,
    )
    db.add(ban)
    user.is_active = False
    db.commit()
    return {"status": "banned", "ban_id": ban.id}


@router.post("/users/{user_id}/unban")
def unban_user(
    user_id: str,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")

    active_bans = (
        db.query(UserBan)
        .filter(UserBan.user_id == user_id, UserBan.is_active == True)
        .all()
    )
    for ban in active_bans:
        ban.is_active = False
    user.is_active = True
    db.commit()
    return {"status": "unbanned"}


# ── Platform stats ───────────────────────────────────────────────

@router.get("/stats")
def platform_stats(
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    from app.models.activity import ScreenSession

    return {
        "total_users": db.query(User).count(),
        "active_users": db.query(User).filter(User.is_active == True).count(),
        "total_orgs": db.query(Organization).count(),
        "active_orgs": db.query(Organization).filter(Organization.is_active == True).count(),
        "total_sessions": db.query(ScreenSession).count(),
        "total_bans": db.query(UserBan).filter(UserBan.is_active == True).count(),
    }


# ── Tariff management ───────────────────────────────────────────

@router.get("/tariffs")
def list_tariffs(
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    plans = db.query(TariffPlan).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "code": p.code,
            "price_monthly": p.price_monthly,
            "price_yearly": p.price_yearly,
            "max_employees": p.max_employees,
            "is_active": p.is_active,
        }
        for p in plans
    ]


@router.post("/tariffs")
def create_tariff(
    name: str,
    code: str,
    price_monthly: float = 0,
    price_yearly: float = 0,
    max_employees: int = 5,
    max_teams: int = 1,
    max_projects: int = 2,
    admin: User = Depends(require_superadmin),
    db: Session = Depends(get_db),
):
    plan = TariffPlan(
        name=name,
        code=code,
        price_monthly=price_monthly,
        price_yearly=price_yearly,
        max_employees=max_employees,
        max_teams=max_teams,
        max_projects=max_projects,
    )
    db.add(plan)
    db.commit()
    return {"id": plan.id, "code": plan.code}
