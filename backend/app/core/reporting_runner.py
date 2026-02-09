from datetime import datetime, timedelta

from app.core.report_exports import ReportExportError, export_org_kpi, export_project_kpi
from app.models.reporting import ReportExport, ReportSchedule
from app.schemas.project_reports import ProjectKPIReport
from app.schemas.reports import KPIOrgReport
from app.api.routes.project_reports import compute_project_kpi_report
from app.api.routes.reports import compute_org_kpi_report


def run_schedule_export(db, org_id: str, schedule: ReportSchedule, export_format: str) -> ReportExport:
    params = _parse_params(schedule.params_json)
    if schedule.report_type == "org_kpi":
        report: KPIOrgReport = compute_org_kpi_report(db, org_id=org_id, **params)
        file_path, size_bytes = export_org_kpi(report, schedule.id, export_format)
    elif schedule.report_type == "project_kpi":
        report: ProjectKPIReport = compute_project_kpi_report(db, org_id=org_id, **params)
        file_path, size_bytes = export_project_kpi(report, schedule.id, export_format)
    else:
        raise ReportExportError("Unsupported report type")

    export = ReportExport(
        org_id=org_id,
        created_by=schedule.created_by,
        report_type=schedule.report_type,
        export_format=export_format,
        params_json=schedule.params_json,
        file_path=file_path,
        size_bytes=size_bytes,
    )
    db.add(export)
    schedule.last_run_at = datetime.utcnow()
    return export


def run_due_schedules(db, org_id: str | None = None, export_format: str = "csv") -> list[ReportExport]:
    now = datetime.utcnow()
    query = db.query(ReportSchedule).filter(ReportSchedule.enabled.is_(True))
    if org_id:
        query = query.filter(ReportSchedule.org_id == org_id)

    schedules = query.all()
    exports: list[ReportExport] = []
    for schedule in schedules:
        last_run = schedule.last_run_at
        due_time = last_run + timedelta(days=schedule.interval_days) if last_run else None
        if due_time and due_time > now:
            continue
        if not due_time and last_run is not None:
            continue

        export = run_schedule_export(db, schedule.org_id, schedule, export_format)
        exports.append(export)

    return exports


def _parse_params(params_json: str) -> dict:
    import json
    from datetime import date

    payload = json.loads(params_json)
    start_date = date.fromisoformat(payload["start_date"]) if payload.get("start_date") else None
    end_date = date.fromisoformat(payload["end_date"]) if payload.get("end_date") else None
    return {
        "start_date": start_date,
        "end_date": end_date,
        "team_id": payload.get("team_id"),
        "project_id": payload.get("project_id"),
    }
