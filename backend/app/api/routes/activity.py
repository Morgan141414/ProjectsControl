import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_token
try:
    from app.services.ai_vision import get_ai_analyzer
    _HAS_AI_VISION = True
except ImportError:
    _HAS_AI_VISION = False
    get_ai_analyzer = None  # type: ignore

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.core.time import utc_now_naive
from app.core.privacy import apply_privacy_rules
from app.core.config import settings
from app.core.storage import StorageError, save_upload
from app.models.activity import ActivityEvent, ScreenRecording, ScreenSession
from app.models.enums import AuditAction, OrgRole, SessionStatus
from app.models.org import OrgMembership
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

# ── Live stream (Zoom/Discord-style): broadcaster → server → viewers ─────────
# Key: (org_id, session_id). Value: broadcaster ws, set of viewer wss, latest frame.
_streams: dict[tuple[str, str], dict] = {}
_streams_lock = asyncio.Lock()


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
    db.flush()
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
    session.ended_at = payload.ended_at or utc_now_naive()

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

        captured_at = item.captured_at or utc_now_naive()
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


def _preview_path(org_id: str, session_id: str) -> Path:
    """Return filesystem path for a live preview image."""
    root = Path(settings.PREVIEWS_PATH).resolve()
    return root / org_id / f"{session_id}.jpg"


async def _analyze_preview_background(image_bytes: bytes, org_id: str, session_id: str) -> None:
    """Background task: analyze preview with AI vision."""
    if not _HAS_AI_VISION or not get_ai_analyzer:
        print("[AI] Vision analysis not available (missing ANTHROPIC_API_KEY or dependency)")
        return

    try:
        analyzer = get_ai_analyzer()
        result = await analyzer.analyze_screenshot(image_bytes, media_type="image/jpeg")

        # Store analysis result (could save to database or cache)
        analysis_path = Path(settings.PREVIEWS_PATH).resolve() / org_id / f"{session_id}_analysis.json"
        analysis_path.parent.mkdir(parents=True, exist_ok=True)

        import json
        analysis_path.write_text(json.dumps(result, indent=2))

        print(f"[AI] Analysis complete for session {session_id}: {result.get('summary', 'N/A')}")
    except Exception as e:
        print(f"[AI] Analysis failed: {e}")


@router.post("/{session_id}/preview")
async def upload_preview(
    org_id: str,
    session_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Upload a lightweight preview frame for a running screen session.

    Used for near real-time monitoring (Discord-like live view).
    Only the owner of the session may push frames.

    NEW: Automatically triggers AI vision analysis in background.
    """
    get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preview must be an image")

    data = file.file.read()
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Preview too large")

    path = _preview_path(org_id, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

    # Trigger AI analysis in background (non-blocking)
    background_tasks.add_task(_analyze_preview_background, data, org_id, session_id)

    return {"status": "ok", "size_bytes": len(data), "ai_analysis": "queued"}


@router.get("/{session_id}/preview")
def get_preview(
    org_id: str,
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    """Return latest preview frame for a session.

    Viewable by the session owner and organization admins/managers.
    """
    membership = get_org_membership(org_id, current_user, db)
    session = db.get(ScreenSession, session_id)
    if not session or session.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.user_id != current_user.id and membership.role not in {
        OrgRole.admin,
        OrgRole.manager,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")

    path = _preview_path(org_id, session_id)
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No preview available")

    return FileResponse(path, media_type="image/jpeg")


@router.websocket("/{session_id}/live")
async def live_stream(
    websocket: WebSocket,
    org_id: str,
    session_id: str,
):
    """Real-time screen stream (Zoom/Discord style). Query: token=...&role=broadcast|viewer."""
    await websocket.accept()
    query = websocket.scope.get("query_string", b"").decode()
    params = {}
    for part in query.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            params[k.strip()] = v.strip()
    token = params.get("token") or params.get("access_token")
    role = (params.get("role") or "viewer").lower()
    if role not in ("broadcast", "viewer"):
        await websocket.close(code=4000)
        return

    user_id = None
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001)
        return

    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        if not user or not user.is_active:
            await websocket.close(code=4001)
            return
        membership = (
            db.query(OrgMembership)
            .filter(OrgMembership.org_id == org_id, OrgMembership.user_id == user.id)
            .first()
        )
        if not membership:
            await websocket.close(code=4003)
            return
        session = db.get(ScreenSession, session_id)
        if not session or session.org_id != org_id:
            await websocket.close(code=4004)
            return
        if role == "broadcast":
            if session.user_id != user.id:
                await websocket.close(code=4003)
                return
        else:
            if session.user_id != user.id and membership.role not in (OrgRole.admin, OrgRole.manager):
                await websocket.close(code=4003)
                return
    finally:
        db.close()

    key = (org_id, session_id)
    async with _streams_lock:
        if key not in _streams:
            _streams[key] = {"broadcaster": None, "viewers": set(), "latest_frame": None}
        slot = _streams[key]

    if role == "broadcast":
        async with _streams_lock:
            if slot["broadcaster"] is not None:
                await websocket.close(code=4009)
                return
            slot["broadcaster"] = websocket
        try:
            while True:
                data = await websocket.receive_bytes()
                if not data or len(data) > 5 * 1024 * 1024:
                    continue
                async with _streams_lock:
                    slot["latest_frame"] = data
                    viewers = list(slot["viewers"])
                for v in viewers:
                    try:
                        await v.send_bytes(data)
                    except Exception:
                        async with _streams_lock:
                            slot["viewers"].discard(v)
        except WebSocketDisconnect:
            pass
        finally:
            async with _streams_lock:
                slot["broadcaster"] = None
                slot["latest_frame"] = None
                if not slot["viewers"]:
                    _streams.pop(key, None)
    else:
        async with _streams_lock:
            slot["viewers"].add(websocket)
            latest = slot.get("latest_frame")
        if latest:
            try:
                await websocket.send_bytes(latest)
            except Exception:
                pass
        try:
            while True:
                await websocket.receive_bytes()
        except WebSocketDisconnect:
            pass
        finally:
            async with _streams_lock:
                slot["viewers"].discard(websocket)
                if slot["broadcaster"] is None and not slot["viewers"]:
                    _streams.pop(key, None)
