from fastapi import APIRouter

from app.api.routes import (
    activity, admin, ai_assistant, ai_kpi, audit, auth, consent,
    daily_reports, invitations, metrics, notifications, orgs,
    payments, performance, privacy, profile, project_reports,
    projects, ratings, recordings, report_exports, reports,
    support, tariffs, tasks, teams, users, vacancies,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(orgs.router)
api_router.include_router(activity.router)
api_router.include_router(admin.router)
api_router.include_router(ai_assistant.router)
api_router.include_router(ai_kpi.router)
api_router.include_router(audit.router)
api_router.include_router(consent.router)
api_router.include_router(daily_reports.router)
api_router.include_router(invitations.router)
api_router.include_router(metrics.router)
api_router.include_router(notifications.router)
api_router.include_router(payments.router)
api_router.include_router(performance.router)
api_router.include_router(privacy.router)
api_router.include_router(profile.router)
api_router.include_router(projects.router)
api_router.include_router(project_reports.router)
api_router.include_router(ratings.router)
api_router.include_router(recordings.router)
api_router.include_router(report_exports.router)
api_router.include_router(reports.router)
api_router.include_router(support.router)
api_router.include_router(tariffs.router)
api_router.include_router(teams.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(vacancies.router)
