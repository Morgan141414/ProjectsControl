# Architecture

## Modules

- app/api/routes: HTTP endpoints and request validation.
- app/models: SQLAlchemy models for core domain.
- app/schemas: Pydantic request/response schemas.
- app/core: configuration, security, and dependencies.
- app/db: database session and metadata.

## Core Domains

- Users: authentication and profiles.
- Organizations: membership and join approvals.
- Teams: scoped visibility within an organization.
- Projects: grouping of teams for reporting and visibility.
- Tasks: assignments, status, and reports.
- Screen sessions: start/stop session metadata for monitoring.
- Activity events: event stream tied to sessions.
- Screen recordings: uploaded files tied to sessions.
- Retention: periodic cleanup of recordings and metadata.
- Retention: cleanup of activity events by policy.
- Metrics: aggregated per-session and per-user productivity signals.
- Privacy rules: redaction or ignoring of sensitive apps/windows.
- Reports: aggregated KPI reports for teams and organizations.
- Reports: project-level KPI summaries.
- Report exports: CSV/JSON files stored locally.
- Report schedules: stored schedules with manual run endpoint.
- Scheduler: background job to run due schedules.
- Notifications: webhook hooks for report exports.
- Audit logs: tamper-evident trail of sensitive actions.

## Data Flow

1) User authenticates and receives JWT.
2) User requests org membership (join code).
3) Admin/manager approves; membership is created.
4) Tasks and teams are created for org.
5) Employee starts a screen session and submits activity events.
6) Managers review sessions and aggregated metrics.

## Security

- JWT bearer tokens.
- Role-based access at org scope.
- Audit logs for privileged actions.

## Storage

- PostgreSQL with UUID-like string ids.
- Tables created on startup for now; use migrations later.
