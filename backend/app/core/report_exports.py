import csv
import json
from pathlib import Path

from app.core.config import settings
from app.schemas.project_reports import ProjectKPIReport
from app.schemas.reports import KPIOrgReport


class ReportExportError(ValueError):
    pass


def _ensure_dir() -> Path:
    base_dir = Path(settings.REPORTS_PATH).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def _write_json(target: Path, payload: dict) -> int:
    data = json.dumps(payload, default=str, ensure_ascii=True, indent=2)
    target.write_text(data, encoding="utf-8")
    return target.stat().st_size


def _write_csv(target: Path, headers: list[str], rows: list[list[str | int | float]]) -> int:
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return target.stat().st_size


def export_org_kpi(report: KPIOrgReport, export_id: str, export_format: str) -> tuple[str, int]:
    base_dir = _ensure_dir()
    if export_format == "json":
        path = base_dir / f"org_kpi_{export_id}.json"
        size = _write_json(path, report.model_dump())
    elif export_format == "csv":
        path = base_dir / f"org_kpi_{export_id}.csv"
        headers = [
            "user_id",
            "full_name",
            "sessions_count",
            "total_events",
            "observed_seconds",
            "idle_seconds",
            "active_seconds",
            "tasks_total",
            "tasks_done",
            "completion_rate",
        ]
        rows = [
            [
                user.user_id,
                user.full_name,
                user.sessions_count,
                user.total_events,
                user.observed_seconds,
                user.idle_seconds,
                user.active_seconds,
                user.tasks_total,
                user.tasks_done,
                user.completion_rate,
            ]
            for user in report.users
        ]
        size = _write_csv(path, headers, rows)
    else:
        raise ReportExportError("Unsupported format")

    if size > settings.REPORTS_MAX_EXPORT_MB * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ReportExportError("Export exceeds size limit")

    return str(path), size


def export_project_kpi(report: ProjectKPIReport, export_id: str, export_format: str) -> tuple[str, int]:
    base_dir = _ensure_dir()
    if export_format == "json":
        path = base_dir / f"project_kpi_{export_id}.json"
        size = _write_json(path, report.model_dump())
    elif export_format == "csv":
        path = base_dir / f"project_kpi_{export_id}.csv"
        headers = [
            "project_id",
            "project_name",
            "teams_count",
            "users_count",
            "sessions_count",
            "total_events",
            "observed_seconds",
            "idle_seconds",
            "active_seconds",
            "tasks_total",
            "tasks_done",
            "completion_rate",
        ]
        rows = [
            [
                item.project_id,
                item.project_name,
                item.teams_count,
                item.users_count,
                item.sessions_count,
                item.total_events,
                item.observed_seconds,
                item.idle_seconds,
                item.active_seconds,
                item.tasks_total,
                item.tasks_done,
                item.completion_rate,
            ]
            for item in report.projects
        ]
        size = _write_csv(path, headers, rows)
    else:
        raise ReportExportError("Unsupported format")

    if size > settings.REPORTS_MAX_EXPORT_MB * 1024 * 1024:
        path.unlink(missing_ok=True)
        raise ReportExportError("Export exceeds size limit")

    return str(path), size
