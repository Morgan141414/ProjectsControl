"""Invitation routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user, get_org_membership, require_role
from app.core.time import utc_now_naive
from app.models.enums import InvitationStatus, OrgRole
from app.models.invitation import Invitation
from app.models.org import OrgMembership
from app.models.user import User
from app.schemas.invitation import InvitationAccept, InvitationCreate, InvitationOut

router = APIRouter(tags=["invitations"])


@router.post("/orgs/{org_id}/invitations", response_model=InvitationOut)
def create_invitation(
    org_id: str,
    body: InvitationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    existing = (
        db.query(Invitation)
        .filter(
            Invitation.org_id == org_id,
            Invitation.email == body.email,
            Invitation.status == InvitationStatus.pending,
        )
        .first()
    )
    if existing:
        raise HTTPException(409, "Invitation already sent")

    invite = Invitation(
        org_id=org_id,
        invited_by=user.id,
        email=body.email,
        role=body.role,
        team_id=body.team_id,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


@router.get("/orgs/{org_id}/invitations")
def list_invitations(
    org_id: str,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner, OrgRole.director, OrgRole.hr_manager, OrgRole.manager})

    q = db.query(Invitation).filter(Invitation.org_id == org_id)
    if status:
        q = q.filter(Invitation.status == status)
    invites = q.order_by(Invitation.created_at.desc()).all()
    return [InvitationOut.model_validate(i) for i in invites]


@router.post("/invitations/accept")
def accept_invitation(
    body: InvitationAccept,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = db.query(Invitation).filter(Invitation.token == body.token).first()
    if not invite:
        raise HTTPException(404, "Invitation not found")
    if invite.status != InvitationStatus.pending:
        raise HTTPException(400, f"Invitation is {invite.status.value}")

    now = utc_now_naive()
    if invite.expires_at and invite.expires_at < now:
        invite.status = InvitationStatus.expired
        db.commit()
        raise HTTPException(400, "Invitation expired")

    if invite.email != user.email:
        raise HTTPException(403, "This invitation is for a different email")

    existing = (
        db.query(OrgMembership)
        .filter(OrgMembership.org_id == invite.org_id, OrgMembership.user_id == user.id)
        .first()
    )
    if existing:
        invite.status = InvitationStatus.accepted
        db.commit()
        raise HTTPException(409, "Already a member")

    membership = OrgMembership(
        org_id=invite.org_id,
        user_id=user.id,
        role=invite.role,
    )
    db.add(membership)
    invite.status = InvitationStatus.accepted
    db.commit()
    return {"status": "accepted", "org_id": invite.org_id}


@router.delete("/orgs/{org_id}/invitations/{invite_id}")
def cancel_invitation(
    org_id: str,
    invite_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    membership = get_org_membership(org_id, user, db)
    require_role(membership, {OrgRole.admin, OrgRole.owner})

    invite = db.get(Invitation, invite_id)
    if not invite or invite.org_id != org_id:
        raise HTTPException(404, "Invitation not found")
    invite.status = InvitationStatus.cancelled
    db.commit()
    return {"status": "cancelled"}
