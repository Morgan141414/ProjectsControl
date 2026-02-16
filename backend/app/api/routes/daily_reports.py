from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.daily_report import DailyReport
from app.models.daily_report_attachment import DailyReportAttachment
from app.models.project import Project
from app.models.user import User
from app.schemas.daily_report import (
    DailyReportAttachmentResponse,
    DailyReportCreate,
    DailyReportResponse,
)

router = APIRouter(prefix="/orgs/{org_id}/daily-reports", tags=["daily-reports"])


@router.post("", response_model=DailyReportResponse)
def create_report(
    org_id: str,
    payload: DailyReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyReport:
    get_org_membership(org_id, current_user, db)

    project = db.get(Project, payload.project_id)
    if not project or project.org_id != org_id:
        raise HTTPException(status_code=404, detail="Project not found")

    report_date = payload.report_date or date.today()
    existing = (
        db.query(DailyReport)
        .filter(
            DailyReport.org_id == org_id,
            DailyReport.project_id == payload.project_id,
            DailyReport.user_id == current_user.id,
            DailyReport.report_date == report_date,
        )
        .first()
    )

    if existing:
        existing.content = payload.content
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    report = DailyReport(
        org_id=org_id,
        project_id=payload.project_id,
        user_id=current_user.id,
        report_date=report_date,
        content=payload.content,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def _attachments_root() -> Path:
    return Path(settings.REPORTS_PATH).resolve()


@router.post(
    "/{report_id}/attachments",
    response_model=DailyReportAttachmentResponse,
)
def upload_attachment(
    org_id: str,
    report_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DailyReportAttachment:
    membership = get_org_membership(org_id, current_user, db)
    _ = membership

    report = db.get(DailyReport, report_id)
    if not report or report.org_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    contents = file.file.read()
    size_bytes = len(contents)
    if size_bytes > max_bytes:
        raise HTTPException(status_code=413, detail="File too large")

    root = _attachments_root()
    target_dir = root / org_id / report_id
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "attachment.bin").name
    dest = target_dir / safe_name
    counter = 1
    while dest.exists():
        dest = target_dir / f"{dest.stem}_{counter}{dest.suffix}"
        counter += 1

    dest.write_bytes(contents)

    attachment = DailyReportAttachment(
        id=new_id(),
        org_id=org_id,
        report_id=report_id,
        filename=safe_name,
        path=str(dest.relative_to(root)),
        mime_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get(
    "/{report_id}/attachments",
    response_model=list[DailyReportAttachmentResponse],
)
def list_attachments(
    org_id: str,
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[DailyReportAttachment]:
    membership = get_org_membership(org_id, current_user, db)
    _ = membership

    report = db.get(DailyReport, report_id)
    if not report or report.org_id != org_id:
        raise HTTPException(status_code=404, detail="Report not found")

    return (
        db.query(DailyReportAttachment)
        .filter(
            DailyReportAttachment.org_id == org_id,
            DailyReportAttachment.report_id == report_id,
        )
        .order_by(DailyReportAttachment.created_at.asc())
        .all()
    )


@router.get(
    "/attachments/{attachment_id}/download",
)
def download_attachment(
    org_id: str,
    attachment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_org_membership(org_id, current_user, db)
    _ = membership

    attachment = db.get(DailyReportAttachment, attachment_id)
    if not attachment or attachment.org_id != org_id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    root = _attachments_root()
    path = root / attachment.path
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.filename,
    )
