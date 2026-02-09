from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.enums import AuditAction, OrgRole
from app.models.privacy import PrivacyRule
from app.models.user import User
from app.schemas.privacy import PrivacyRuleCreate, PrivacyRuleResponse, PrivacyRuleUpdate

router = APIRouter(prefix="/orgs/{org_id}/privacy/rules", tags=["privacy"])


@router.get("", response_model=list[PrivacyRuleResponse])
def list_rules(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PrivacyRule]:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return (
        db.query(PrivacyRule)
        .filter(PrivacyRule.org_id == org_id)
        .order_by(PrivacyRule.created_at.desc())
        .all()
    )


@router.post("", response_model=PrivacyRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    org_id: str,
    payload: PrivacyRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrivacyRule:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    rule = PrivacyRule(
        org_id=org_id,
        target=payload.target,
        match_type=payload.match_type,
        pattern=payload.pattern,
        action=payload.action,
        enabled=payload.enabled,
    )
    db.add(rule)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="privacy_rule",
        entity_id=rule.id,
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.patch("/{rule_id}", response_model=PrivacyRuleResponse)
def update_rule(
    org_id: str,
    rule_id: str,
    payload: PrivacyRuleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PrivacyRule:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    rule = db.get(PrivacyRule, rule_id)
    if not rule or rule.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    if payload.pattern is not None:
        rule.pattern = payload.pattern
    if payload.action is not None:
        rule.action = payload.action
    if payload.enabled is not None:
        rule.enabled = payload.enabled

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="privacy_rule",
        entity_id=rule.id,
    )
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(
    org_id: str,
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    rule = db.get(PrivacyRule, rule_id)
    if not rule or rule.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found")

    db.delete(rule)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.delete,
        entity_type="privacy_rule",
        entity_id=rule.id,
    )
    db.commit()
