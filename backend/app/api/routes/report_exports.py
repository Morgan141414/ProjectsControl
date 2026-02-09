import json
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.audit import log_audit
from app.core.deps import get_current_user, get_db, get_org_membership, require_role
from app.core.report_exports import ReportExportError, export_org_kpi, export_project_kpi
from app.core.reporting_runner import run_schedule_export
from app.core.notifications import send_notification
from app.models.enums import AuditAction, NotificationEvent, OrgRole
from app.models.reporting import ReportExport, ReportSchedule
from app.models.user import User
from app.schemas.reporting import ReportExportResponse, ReportScheduleCreate, ReportScheduleResponse
from app.api.routes.project_reports import compute_project_kpi_report
from app.api.routes.reports import compute_org_kpi_report

router = APIRouter(prefix="/orgs/{org_id}/reports", tags=["reports"])


def _serialize_params(
    start_date: date | None,
    end_date: date | None,
    team_id: str | None,
    project_id: str | None,
) -> str:
    return json.dumps(
        {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "team_id": team_id,
            "project_id": project_id,
        }
    )


def _parse_params(params_json: str) -> dict:
    payload = json.loads(params_json)
    start_date = date.fromisoformat(payload["start_date"]) if payload.get("start_date") else None
    end_date = date.fromisoformat(payload["end_date"]) if payload.get("end_date") else None
    return {
        "start_date": start_date,
        "end_date": end_date,
        "team_id": payload.get("team_id"),
        "project_id": payload.get("project_id"),
    }


def _save_export(
    db: Session,
    org_id: str,
    user_id: str,
    report_type: str,
    export_format: str,
    params_json: str,
    file_path: str,
    size_bytes: int,
) -> ReportExport:
    export = ReportExport(
        org_id=org_id,
        created_by=user_id,
        report_type=report_type,
        export_format=export_format,
        params_json=params_json,
        file_path=file_path,
        size_bytes=size_bytes,
    )
    db.add(export)
    log_audit(
        db,
        org_id=org_id,
        actor_id=user_id,
        action=AuditAction.create,
        entity_type="report_export",
        entity_id=export.id,
    )
    return export


@router.post("/exports/org-kpi", response_model=ReportExportResponse)
def export_org_kpi_report(
    org_id: str,
    export_format: str = Query(default="csv", pattern="^(csv|json)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportExport:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    report = compute_org_kpi_report(
        db,
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        team_id=team_id,
        project_id=project_id,
    )
    params_json = _serialize_params(start_date, end_date, team_id, project_id)
    export_id = current_user.id + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    try:
        file_path, size_bytes = export_org_kpi(report, export_id, export_format)
    except ReportExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    export = _save_export(
        db,
        org_id=org_id,
        user_id=current_user.id,
        report_type="org_kpi",
        export_format=export_format,
        params_json=params_json,
        file_path=file_path,
        size_bytes=size_bytes,
    )
    db.commit()
    db.refresh(export)
    send_notification(
        db,
        org_id=org_id,
        event_type=NotificationEvent.report_export_ready,
        payload={
            "export_id": export.id,
            "report_type": export.report_type,
            "export_format": export.export_format,
            "size_bytes": export.size_bytes,
        },
    )
    return export


@router.post("/exports/project-kpi", response_model=ReportExportResponse)
def export_project_kpi_report(
    org_id: str,
    export_format: str = Query(default="csv", pattern="^(csv|json)$"),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportExport:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    report = compute_project_kpi_report(
        db,
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
    )
    params_json = _serialize_params(start_date, end_date, None, None)
    export_id = current_user.id + "-" + datetime.utcnow().strftime("%Y%m%d%H%M%S%f")

    try:
        file_path, size_bytes = export_project_kpi(report, export_id, export_format)
    except ReportExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    export = _save_export(
        db,
        org_id=org_id,
        user_id=current_user.id,
        report_type="project_kpi",
        export_format=export_format,
        params_json=params_json,
        file_path=file_path,
        size_bytes=size_bytes,
    )
    db.commit()
    db.refresh(export)
    send_notification(
        db,
        org_id=org_id,
        event_type=NotificationEvent.report_export_ready,
        payload={
            "export_id": export.id,
            "report_type": export.report_type,
            "export_format": export.export_format,
            "size_bytes": export.size_bytes,
        },
    )
    return export


@router.get("/exports", response_model=list[ReportExportResponse])
def list_exports(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportExport]:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return (
        db.query(ReportExport)
        .filter(ReportExport.org_id == org_id)
        .order_by(ReportExport.created_at.desc())
        .all()
    )


@router.get("/exports/{export_id}/download")
def download_export(
    org_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    export = db.get(ReportExport, export_id)
    if not export or export.org_id != org_id:
        raise HTTPException(status_code=404, detail="Export not found")

    path = Path(export.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not available")

    return FileResponse(path)


@router.post("/schedules", response_model=ReportScheduleResponse)
def create_schedule(
    org_id: str,
    payload: ReportScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportSchedule:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    if payload.report_type not in {"org_kpi", "project_kpi"}:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    params_json = _serialize_params(
        payload.start_date,
        payload.end_date,
        payload.team_id,
        payload.project_id,
    )
    schedule = ReportSchedule(
        org_id=org_id,
        created_by=current_user.id,
        report_type=payload.report_type,
        params_json=params_json,
        interval_days=payload.interval_days,
        enabled=True,
    )
    db.add(schedule)
    log_audit(
        db,
        org_id=org_id,
        actor_id=current_user.id,
        action=AuditAction.create,
        entity_type="report_schedule",
        entity_id=schedule.id,
    )
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/schedules", response_model=list[ReportScheduleResponse])
def list_schedules(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReportSchedule]:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    return (
        db.query(ReportSchedule)
        .filter(ReportSchedule.org_id == org_id)
        .order_by(ReportSchedule.created_at.desc())
        .all()
    )


@router.post("/schedules/{schedule_id}/run", response_model=ReportExportResponse)
def run_schedule(
    org_id: str,
    schedule_id: str,
    export_format: str = Query(default="csv", pattern="^(csv|json)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportExport:
    membership = get_org_membership(org_id, current_user, db)
    require_role(membership, {OrgRole.admin, OrgRole.manager})

    schedule = db.get(ReportSchedule, schedule_id)
    if not schedule or schedule.org_id != org_id:
        raise HTTPException(status_code=404, detail="Schedule not found")
    if not schedule.enabled:
        raise HTTPException(status_code=400, detail="Schedule disabled")

    try:
        export = run_schedule_export(db, org_id, schedule, export_format)
    except ReportExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    export.created_by = current_user.id
    db.commit()
    db.refresh(export)
    send_notification(
        db,
        org_id=org_id,
        event_type=NotificationEvent.report_export_ready,
        payload={
            "export_id": export.id,
            "report_type": export.report_type,
            "export_format": export.export_format,
            "size_bytes": export.size_bytes,
        },
    )
    return export
