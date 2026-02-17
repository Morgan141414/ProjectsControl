from enum import Enum


class PlatformRole(str, Enum):
    superadmin = "superadmin"


class OrgRole(str, Enum):
    owner = "owner"
    director = "director"
    hr_manager = "hr_manager"
    accountant = "accountant"
    project_manager = "project_manager"
    admin = "admin"
    manager = "manager"
    member = "member"


class TeamRole(str, Enum):
    head = "head"
    lead = "lead"
    senior = "senior"
    specialist = "specialist"
    intern = "intern"
    member = "member"


class JoinStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class SessionStatus(str, Enum):
    active = "active"
    stopped = "stopped"


class ActivityType(str, Enum):
    app = "app"
    input = "input"
    idle = "idle"
    system = "system"


class AuditAction(str, Enum):
    create = "create"
    update = "update"
    delete = "delete"
    approve = "approve"
    reject = "reject"
    login = "login"
    ban = "ban"
    unban = "unban"
    suspend = "suspend"
    activate = "activate"


class PrivacyTarget(str, Enum):
    app_name = "app_name"
    window_title = "window_title"


class MatchType(str, Enum):
    equals = "equals"
    contains = "contains"
    regex = "regex"


class PrivacyAction(str, Enum):
    redact = "redact"
    ignore = "ignore"


class NotificationEvent(str, Enum):
    report_export_ready = "report_export_ready"
    ticket_created = "ticket_created"
    ticket_updated = "ticket_updated"
    vacancy_application = "vacancy_application"


class ScorePeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"


class CertificateStatus(str, Enum):
    active = "active"
    suspended = "suspended"
    expired = "expired"
    revoked = "revoked"


class TicketCategory(str, Enum):
    bug_report = "bug_report"
    feature_request = "feature_request"
    billing = "billing"
    account = "account"
    organization = "organization"
    technical = "technical"
    security = "security"
    other = "other"


class TicketPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TicketStatus(str, Enum):
    open = "open"
    in_progress = "in_progress"
    waiting_for_user = "waiting_for_user"
    waiting_for_support = "waiting_for_support"
    resolved = "resolved"
    closed = "closed"
    reopened = "reopened"


class EmploymentType(str, Enum):
    full_time = "full_time"
    part_time = "part_time"
    contract = "contract"
    internship = "internship"


class ApplicationStatus(str, Enum):
    pending = "pending"
    reviewing = "reviewing"
    interview = "interview"
    offered = "offered"
    rejected = "rejected"
    withdrawn = "withdrawn"


class InvitationStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    cancelled = "cancelled"


class PaymentType(str, Enum):
    ban_appeal = "ban_appeal"
    tariff_subscription = "tariff_subscription"
    tariff_renewal = "tariff_renewal"
    ai_addon = "ai_addon"
    premium_feature = "premium_feature"


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    refunded = "refunded"


class PaymentProvider(str, Enum):
    yookassa = "yookassa"
    stripe = "stripe"
    tinkoff = "tinkoff"


class SubscriptionStatus(str, Enum):
    active = "active"
    expired = "expired"
    cancelled = "cancelled"
    suspended = "suspended"


class SupportLevel(str, Enum):
    community = "community"
    standard = "standard"
    priority = "priority"
    dedicated = "dedicated"


class BanType(str, Enum):
    temporary = "temporary"
    permanent = "permanent"


class BanAppealStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class BadgeLevel(str, Enum):
    platinum = "platinum"
    gold = "gold"
    silver = "silver"
    bronze = "bronze"
    none = "none"


class RatingTrend(str, Enum):
    up = "up"
    stable = "stable"
    down = "down"


class OrgBadge(str, Enum):
    top_employer = "top_employer"
    rising_star = "rising_star"
    reliable = "reliable"
    none = "none"


class OrgTier(str, Enum):
    enterprise = "enterprise"
    professional = "professional"
    standard = "standard"
    starter = "starter"


class VideoRoomType(str, Enum):
    one_on_one = "one_on_one"
    group = "group"
    webinar = "webinar"
    standup = "standup"


class VideoParticipantRole(str, Enum):
    host = "host"
    co_host = "co_host"
    participant = "participant"
    viewer = "viewer"
