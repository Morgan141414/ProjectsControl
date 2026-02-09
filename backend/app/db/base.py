from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from app.models import ai_score, activity, consent, daily_report, notification, org, privacy, project, reporting, task, team, user  # noqa: E402,F401
