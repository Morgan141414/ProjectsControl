from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.core.privacy import apply_privacy_rules
from app.core.config import settings
from app.core.storage import StorageError, save_upload
from app.models.activity import ActivityEvent, ScreenRecording, ScreenSession
from app.models.enums import AuditAction, OrgRole, SessionStatus
from app.models.privacy import PrivacyRule
from app.models.user import User
from app.utils.ids import new_id
from app.schemas.activity import (
    ActivityEventCreate,
    ActivityEventResponse,
    RecordingResponse,
    SessionResponse,
    SessionStart,
    SessionStop,
)

router = APIRouter(prefix="/orgs/{org_id}/sessions", tags=["sessions"])


@router.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    org_id: str,
    payload: SessionStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScreenSession:
    get_org_membership(org_id, current_user, db)

    session = ScreenSession(
        org_id=org_id,
        user_id=current_user.id,
        status=SessionStatus.active,
        device_name=payload.device_name,
        os_name=payload.os_name,
    )
    db.add(session)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="screen_session",
        entity_id=session.id,
    )
    db.commit()
    db.refresh(session)
    return session


@router.post("/{session_id}/stop", response_model=SessionResponse)
def stop_session(
    org_id: str,
    session_id: str,
    payload: SessionStop,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScreenSession:
    get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    session.status = SessionStatus.stopped
    session.ended_at = payload.ended_at or datetime.utcnow()

    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.update,
        entity_type="screen_session",
        entity_id=session.id,
    )
    db.commit()
    db.refresh(session)
    return session


@router.get("/me", response_model=list[SessionResponse])
def list_my_sessions(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScreenSession]:
    get_org_membership(org_id, current_user, db)
    return (
        db.query(ScreenSession)
        .filter(ScreenSession.org_id == org_id, ScreenSession.user_id == current_user.id)
        .order_by(ScreenSession.started_at.desc())
        .all()
    )


@router.get("", response_model=list[SessionResponse])
def list_org_sessions(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScreenSession]:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return (
        db.query(ScreenSession)
        .filter(ScreenSession.org_id == org_id)
        .order_by(ScreenSession.started_at.desc())
        .all()
    )


@router.post("/events/bulk", response_model=list[ActivityEventResponse])
def create_events_bulk(
    org_id: str,
    payload: list[ActivityEventCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ActivityEvent]:
    get_org_membership(org_id, current_user, db)

    events: list[ActivityEvent] = []
    rules = (
        db.query(PrivacyRule)
        .filter(PrivacyRule.org_id == org_id, PrivacyRule.enabled.is_(True))
        .all()
    )
    for item in payload:
        session = db.get(ScreenSession, item.session_id)
        if not session or session.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid session")
        if session.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

        captured_at = item.captured_at or datetime.utcnow()
        app_name, window_title, ignore = apply_privacy_rules(
            rules,
            item.app_name,
            item.window_title,
        )
        if ignore:
            continue
        events.append(
            ActivityEvent(
                session_id=item.session_id,
                org_id=org_id,
                user_id=current_user.id,
                event_type=item.event_type,
                captured_at=captured_at,
                app_name=app_name,
                window_title=window_title,
                idle_seconds=item.idle_seconds,
                notes=item.notes,
            )
        )

    db.add_all(events)
    db.commit()
    for event in events:
        db.refresh(event)
    return events


@router.post(
    "/{session_id}/recordings",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_recording(
    org_id: str,
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScreenRecording:
    get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    recording_id = new_id()
    try:
        file_path, size_bytes, checksum = save_upload(file, org_id, session_id, recording_id)
    except StorageError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    recording = ScreenRecording(
        id=recording_id,
        session_id=session_id,
        org_id=org_id,
        user_id=current_user.id,
        file_path=file_path,
        content_type=file.content_type,
        size_bytes=size_bytes,
        checksum_sha256=checksum,
    )
    db.add(recording)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="screen_recording",
        entity_id=recording.id,
    )
    db.commit()
    db.refresh(recording)
    return recording


@router.get("/{session_id}/recordings", response_model=list[RecordingResponse])
def list_recordings(
    org_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScreenRecording]:
    membership = get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.user_id != current_user.id and membership.role not in {
        OrgRole.admin,
        OrgRole.manager,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    return (
        db.query(ScreenRecording)
        .filter(ScreenRecording.session_id == session_id)
        .order_by(ScreenRecording.created_at.desc())
        .all()
    )
