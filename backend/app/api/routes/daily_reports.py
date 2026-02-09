from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, get_org_membership
from app.models.daily_report import DailyReport
from app.models.project import Project
from app.models.user import User
from app.schemas.daily_report import DailyReportCreate, DailyReportResponse

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
