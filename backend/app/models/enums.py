from enum import Enum


class OrgRole(str, Enum):
    admin = "admin"
    manager = "manager"
    member = "member"


class JoinStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TaskStatus(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TeamRole(str, Enum):
    member = "member"
    lead = "lead"


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


class ScorePeriod(str, Enum):
    daily = "daily"
    weekly = "weekly"
