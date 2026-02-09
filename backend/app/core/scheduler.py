from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.notifications import send_notification
from app.core.reporting_runner import run_due_schedules
from app.api.routes.ai_kpi import _period_bounds, _upsert_snapshot
from app.api.routes.reports import compute_org_kpi_report
from app.models.enums import NotificationEvent, ScorePeriod
from app.models.org import Organization
from app.db.session import SessionLocal

_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(_tick, "interval", seconds=settings.SCHEDULE_TICK_SECONDS)
    _scheduler.add_job(_run_daily_ai_snapshots, "cron", hour=2, minute=0)
    _scheduler.add_job(_run_weekly_ai_snapshots, "cron", day_of_week="sun", hour=23, minute=59)
    _scheduler.start()


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def _tick() -> None:
    with SessionLocal() as db:
        exports = run_due_schedules(db)
        if exports:
            db.commit()
            for export in exports:
                send_notification(
                    db,
                    org_id=export.org_id,
                    event_type=NotificationEvent.report_export_ready,
                    payload={
                        "export_id": export.id,
                        "report_type": export.report_type,
                        "export_format": export.export_format,
                        "size_bytes": export.size_bytes,
                    },
                )


def _run_daily_ai_snapshots() -> None:
    target_day = date.today() - timedelta(days=1)
    _build_ai_snapshots(ScorePeriod.daily, target_day, target_day)


def _run_weekly_ai_snapshots() -> None:
    as_of = date.today()
    period_start, period_end = _period_bounds(as_of, ScorePeriod.weekly)
    _build_ai_snapshots(ScorePeriod.weekly, period_start, period_end)


def _build_ai_snapshots(period: ScorePeriod, period_start: date, period_end: date) -> None:
    with SessionLocal() as db:
        orgs = db.query(Organization).all()
        snapshots_count = 0
        for org in orgs:
            report = compute_org_kpi_report(
                db,
                org.id,
                start_date=period_start,
                end_date=period_end,
            )
            for row in report.users:
                _upsert_snapshot(
                    db,
                    org_id=org.id,
                    period_type=period,
                    period_start=period_start,
                    period_end=period_end,
                    user_row=row,
                )
                snapshots_count += 1
        if snapshots_count:
            db.commit()
