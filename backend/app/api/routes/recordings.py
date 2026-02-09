from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.core.retention import cleanup_recordings
from app.models.activity import ScreenRecording, ScreenSession
from app.models.enums import AuditAction, OrgRole
from app.models.user import User
from app.schemas.activity import RecordingCleanupResponse

router = APIRouter(prefix="/orgs/{org_id}/recordings", tags=["recordings"])


@router.get("/{recording_id}/download")
def download_recording(
    org_id: str,
    recording_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    membership = get_org_membership(org_id, current_user, db)
    recording = db.get(ScreenRecording, recording_id)
    if not recording or recording.org_id != org_id:
        raise HTTPException(status_code=404, detail="Recording not found")

    session = db.get(ScreenSession, recording.session_id)
    if session and session.user_id != current_user.id and membership.role not in {
        OrgRole.admin,
        OrgRole.manager,
    }:
        raise HTTPException(status_code=403, detail="Not allowed")

    path = Path(recording.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not available")

    return FileResponse(path)


@router.post("/cleanup", response_model=RecordingCleanupResponse)
def cleanup_recordings_endpoint(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RecordingCleanupResponse:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    deleted_count = cleanup_recordings(db, org_id=org_id)
    if deleted_count:
        log_audit(
            db,
            org_id=org_id,
            actor_id=current_user.id,
            action=AuditAction.delete,
            entity_type="screen_recording",
            entity_id="bulk_cleanup",
            details=f"deleted={deleted_count}",
        )
    db.commit()
    return RecordingCleanupResponse(
        deleted_count=deleted_count,
        retention_days=settings.RETENTION_DAYS,
    )
