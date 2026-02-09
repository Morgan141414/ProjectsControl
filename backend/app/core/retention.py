from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activity import ActivityEvent, ScreenRecording


def cleanup_recordings(db: Session, org_id: str | None = None) -> int:
    if settings.RETENTION_DAYS <= 0:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=settings.RETENTION_DAYS)
    query = db.query(ScreenRecording).filter(ScreenRecording.created_at < cutoff)
    if org_id:
        query = query.filter(ScreenRecording.org_id == org_id)

    records = query.all()
    for record in records:
        path = Path(record.file_path)
        if path.exists():
            path.unlink()
        db.delete(record)

    return len(records)


def cleanup_activity_events(db: Session, org_id: str | None = None) -> int:
    if settings.EVENTS_RETENTION_DAYS <= 0:
        return 0

    cutoff = datetime.utcnow() - timedelta(days=settings.EVENTS_RETENTION_DAYS)
    query = db.query(ActivityEvent).filter(ActivityEvent.captured_at < cutoff)
    if org_id:
        query = query.filter(ActivityEvent.org_id == org_id)

    records = query.all()
    for record in records:
        db.delete(record)

    return len(records)
