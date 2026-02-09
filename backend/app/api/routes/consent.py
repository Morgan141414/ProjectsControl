from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.consent import ConsentRecord
from app.models.user import User
from app.schemas.consent import ConsentRequest, ConsentStatus

router = APIRouter(prefix="/orgs/{org_id}/consent", tags=["consent"])


@router.get("/me", response_model=ConsentStatus)
def get_consent(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentStatus:
    get_org_membership(org_id, current_user, db)

    record = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.org_id == org_id, ConsentRecord.user_id == current_user.id)
        .first()
    )
    if not record:
        return ConsentStatus(
            org_id=org_id,
            user_id=current_user.id,
            accepted=False,
            accepted_at=None,
            policy_version=None,
        )

    return ConsentStatus(
        org_id=org_id,
        user_id=current_user.id,
        accepted=True,
        accepted_at=record.accepted_at,
        policy_version=record.policy_version,
    )


@router.post("/accept", response_model=ConsentStatus)
def accept_consent(
    org_id: str,
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentStatus:
    get_org_membership(org_id, current_user, db)

    record = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.org_id == org_id, ConsentRecord.user_id == current_user.id)
        .first()
    )

    if record:
        record.policy_version = payload.policy_version
    else:
        record = ConsentRecord(
            org_id=org_id,
            user_id=current_user.id,
            policy_version=payload.policy_version,
        )
        db.add(record)

    db.commit()
    db.refresh(record)

    return ConsentStatus(
        org_id=org_id,
        user_id=current_user.id,
        accepted=True,
        accepted_at=record.accepted_at,
        policy_version=record.policy_version,
    )
