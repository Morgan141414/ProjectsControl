from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.models.enums import AuditAction, OrgRole
from app.models.notification import NotificationHook
from app.models.user import User
from app.schemas.notification import (
    NotificationHookCreate,
    NotificationHookResponse,
    NotificationHookUpdate,
)

router = APIRouter(prefix="/orgs/{org_id}/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationHookResponse])
def list_hooks(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationHook]:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return (
        db.query(NotificationHook)
        .filter(NotificationHook.org_id == org_id)
        .order_by(NotificationHook.created_at.desc())
        .all()
    )


@router.post("", response_model=NotificationHookResponse, status_code=status.HTTP_201_CREATED)
def create_hook(
    org_id: str,
    payload: NotificationHookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationHook:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    hook = NotificationHook(
        org_id=org_id,
        event_type=payload.event_type,
        url=payload.url,
        enabled=payload.enabled,
    )
    db.add(hook)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="notification_hook",
        entity_id=hook.id,
    )
    db.commit()
    db.refresh(hook)
    return hook


@router.patch("/{hook_id}", response_model=NotificationHookResponse)
def update_hook(
    org_id: str,
    hook_id: str,
    payload: NotificationHookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationHook:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    hook = db.get(NotificationHook, hook_id)
    if not hook or hook.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    if payload.url is not None:
        hook.url = payload.url
    if payload.enabled is not None:
        hook.enabled = payload.enabled

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="notification_hook",
        entity_id=hook.id,
    )
    db.commit()
    db.refresh(hook)
    return hook


@router.delete("/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hook(
    org_id: str,
    hook_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    hook = db.get(NotificationHook, hook_id)
    if not hook or hook.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Hook not found")

    db.delete(hook)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.delete,
        entity_type="notification_hook",
        entity_id=hook.id,
    )
    db.commit()
