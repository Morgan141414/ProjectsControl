import argparse
from datetime import date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.core.time import utc_now_naive
from app.db.session import SessionLocal
from app.models.activity import ActivityEvent, ScreenSession
from app.models.enums import ActivityType, OrgRole, SessionStatus, TaskStatus
from app.models.org import OrgMembership, Organization
from app.models.project import Project
from app.models.task import Task
from app.models.team import Team, TeamMembership
from app.models.user import User
from app.utils.ids import new_id


def get_or_create_user(db: Session, email: str, full_name: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()
    return user


def seed(db: Session) -> dict[str, str]:
    org = Organization(name="Demo Org")
    db.add(org)
    db.flush()

    admin = get_or_create_user(db, "admin@example.com", "Admin User", "AdminPass123")
    manager = get_or_create_user(db, "manager@example.com", "Manager User", "ManagerPass123")
    member = get_or_create_user(db, "member@example.com", "Member User", "MemberPass123")

    db.add_all(
        [
            OrgMembership(org_id=org.id, user_id=admin.id, role=OrgRole.admin),
            OrgMembership(org_id=org.id, user_id=manager.id, role=OrgRole.manager),
            OrgMembership(org_id=org.id, user_id=member.id, role=OrgRole.member),
        ]
    )

    project = Project(org_id=org.id, name="Project Alpha", description="Seed project")
    db.add(project)
    db.flush()

    team = Team(org_id=org.id, project_id=project.id, name="Alpha Team")
    db.add(team)
    db.flush()

    db.add_all(
        [
            TeamMembership(team_id=team.id, user_id=admin.id),
            TeamMembership(team_id=team.id, user_id=manager.id),
            TeamMembership(team_id=team.id, user_id=member.id),
        ]
    )

    today = date.today()
    tasks = [
        Task(
            org_id=org.id,
            team_id=team.id,
            assignee_id=member.id,
            title="Setup dev environment",
            description="Install dependencies and run the API",
            status=TaskStatus.in_progress,
            due_date=today,
        ),
        Task(
            org_id=org.id,
            team_id=team.id,
            assignee_id=member.id,
            title="Review onboarding docs",
            description="Read architecture and API docs",
            status=TaskStatus.done,
            due_date=today,
            report="Reviewed docs",
        ),
    ]
    db.add_all(tasks)

    session = ScreenSession(
        org_id=org.id,
        user_id=member.id,
        status=SessionStatus.active,
        started_at=utc_now_naive() - timedelta(hours=2),
        device_name="Workstation",
        os_name="Windows",
    )
    db.add(session)
    db.flush()

    events = []
    base = session.started_at
    for index in range(6):
        events.append(
            ActivityEvent(
                session_id=session.id,
                org_id=org.id,
                user_id=member.id,
                event_type=ActivityType.app,
                captured_at=base + timedelta(minutes=index * 10),
                app_name="VS Code",
                window_title="ProjectsControl",
            )
        )
    events.append(
        ActivityEvent(
            session_id=session.id,
            org_id=org.id,
            user_id=member.id,
            event_type=ActivityType.idle,
            captured_at=base + timedelta(minutes=70),
            idle_seconds=300,
        )
    )
    db.add_all(events)

    # ── Seed superadmin ─────────────────────────────────────────
    superadmin = get_or_create_user(db, "superadmin@projectscontrol.io", "Super Admin", "SuperAdmin123!")
    superadmin.is_superadmin = True

    # ── Seed tariff plans ────────────────────────────────────────
    from app.models.tariff import TariffPlan
    if not db.query(TariffPlan).first():
        plans = [
            TariffPlan(
                name="Starter", code="starter",
                description="Free plan for small teams",
                price_monthly=0, price_yearly=0,
                max_employees=5, max_teams=1, max_projects=2,
                max_storage_gb=1, max_ai_tokens_monthly=10000,
                support_level="community", support_response_hours=72,
                has_ai_assistant=False, has_video_calls=False,
            ),
            TariffPlan(
                name="Business", code="business",
                description="For growing companies",
                price_monthly=4990, price_yearly=49900,
                max_employees=50, max_teams=10, max_projects=20,
                max_storage_gb=50, max_ai_tokens_monthly=500000,
                support_level="standard", support_response_hours=24,
                has_ai_assistant=True, has_video_calls=True,
                has_api_access=True,
            ),
            TariffPlan(
                name="Enterprise", code="enterprise",
                description="For large organizations",
                price_monthly=14990, price_yearly=149900,
                max_employees=9999, max_teams=9999, max_projects=9999,
                max_storage_gb=500, max_ai_tokens_monthly=5000000,
                support_level="dedicated", support_response_hours=4,
                has_ai_assistant=True, has_video_calls=True,
                has_api_access=True, has_custom_branding=True,
                has_pdf_export=True,
            ),
        ]
        db.add_all(plans)

    # ── Seed FAQ articles ────────────────────────────────────────
    from app.models.support import FAQArticle
    if not db.query(FAQArticle).first():
        faqs = [
            FAQArticle(
                category="getting_started",
                title="How to create an organization?",
                content="After registration, choose 'Admin' role and follow the organization wizard to create your company.",
            ),
            FAQArticle(
                category="getting_started",
                title="How to join an existing organization?",
                content="Choose 'Employee' role during onboarding, then search for your company or enter the join code.",
            ),
            FAQArticle(
                category="billing",
                title="How do tariff plans work?",
                content="We offer Starter (free), Business, and Enterprise plans. Upgrade anytime from your organization settings.",
            ),
        ]
        db.add_all(faqs)

    return {
        "org_id": org.id,
        "join_code": org.join_code,
        "project_id": project.id,
        "team_id": team.id,
        "admin_email": admin.email,
        "manager_email": manager.email,
        "member_email": member.email,
        "superadmin_email": superadmin.email,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete all rows before seeding")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.reset:
            # Delete in reverse-dependency order (children first)
            for table in [
                # Activity & recordings
                "screen_recordings",
                "activity_events",
                "screen_sessions",
                # AI
                "ai_conversations",
                "ai_company_assistants",
                # Video
                "video_recordings",
                "video_participants",
                "video_rooms",
                # Support
                "ticket_messages",
                "support_tickets",
                "faq_articles",
                # Ratings
                "employee_monthly_ratings",
                "employee_public_ratings",
                "org_public_ratings",
                # Payments & billing
                "ban_appeals",
                "user_bans",
                "payments",
                "subscriptions",
                "tariff_plans",
                # HR
                "vacancy_applications",
                "vacancies",
                "invitations",
                # Certificates
                "organization_certificates",
                # Scoring & analytics
                "ai_score_snapshots",
                # Reports
                "daily_report_attachments",
                "report_exports",
                "report_schedules",
                "daily_reports",
                # Audit & privacy
                "audit_logs",
                "consent_records",
                "privacy_rules",
                "notification_hooks",
                # Core
                "org_join_requests",
                "tasks",
                "team_memberships",
                "teams",
                "projects",
                "org_memberships",
                "organizations",
                "users",
            ]:
                db.execute(text(f"DELETE FROM {table}"))
        info = seed(db)
        db.commit()

    print("Seed completed:")
    for key, value in info.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
