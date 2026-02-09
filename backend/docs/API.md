# API Overview

## Auth

- POST /auth/register
- POST /auth/login

## Organizations

- POST /orgs
- GET /orgs/{org_id}
- POST /orgs/join-request
- GET /orgs/{org_id}/join-requests
- POST /orgs/{org_id}/join-requests/{request_id}/approve
- POST /orgs/{org_id}/join-requests/{request_id}/reject

## Teams

- POST /orgs/{org_id}/teams
- GET /orgs/{org_id}/teams?project_id=PROJECT_ID
- GET /orgs/{org_id}/teams/me?project_id=PROJECT_ID
- POST /orgs/{org_id}/teams/{team_id}/members
- PATCH /orgs/{org_id}/teams/{team_id}

## Projects

- POST /orgs/{org_id}/projects
- GET /orgs/{org_id}/projects
- GET /orgs/{org_id}/projects/{project_id}
- PATCH /orgs/{org_id}/projects/{project_id}
## Notifications

- GET /orgs/{org_id}/notifications
- POST /orgs/{org_id}/notifications
- PATCH /orgs/{org_id}/notifications/{hook_id}
- DELETE /orgs/{org_id}/notifications/{hook_id}

## Users

- GET /orgs/{org_id}/users

## Tasks

- POST /orgs/{org_id}/tasks
- GET /orgs/{org_id}/tasks/today?project_id=PROJECT_ID
- PATCH /orgs/{org_id}/tasks/{task_id}

## Sessions & Activity

- POST /orgs/{org_id}/sessions/start
- POST /orgs/{org_id}/sessions/{session_id}/stop
- GET /orgs/{org_id}/sessions/me
- GET /orgs/{org_id}/sessions
- POST /orgs/{org_id}/sessions/events/bulk
- POST /orgs/{org_id}/sessions/events/cleanup
- POST /orgs/{org_id}/sessions/{session_id}/recordings
- GET /orgs/{org_id}/sessions/{session_id}/recordings

## Recordings

- GET /orgs/{org_id}/recordings/{recording_id}/download
- POST /orgs/{org_id}/recordings/cleanup

## Audit

- GET /orgs/{org_id}/audit

## Metrics

- GET /orgs/{org_id}/metrics/sessions/{session_id}
- GET /orgs/{org_id}/metrics/users/{user_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&project_id=PROJECT_ID

## Privacy Rules

- GET /orgs/{org_id}/privacy/rules
- POST /orgs/{org_id}/privacy/rules
- PATCH /orgs/{org_id}/privacy/rules/{rule_id}
- DELETE /orgs/{org_id}/privacy/rules/{rule_id}

## Reports

- GET /orgs/{org_id}/reports/kpi?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&team_id=TEAM_ID&project_id=PROJECT_ID
- GET /orgs/{org_id}/reports/projects/kpi?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD

## Report Exports

- POST /orgs/{org_id}/reports/exports/org-kpi?export_format=csv|json&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&team_id=TEAM_ID&project_id=PROJECT_ID
- POST /orgs/{org_id}/reports/exports/project-kpi?export_format=csv|json&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
- GET /orgs/{org_id}/reports/exports
- GET /orgs/{org_id}/reports/exports/{export_id}/download

## Report Schedules

- POST /orgs/{org_id}/reports/schedules
- GET /orgs/{org_id}/reports/schedules
- POST /orgs/{org_id}/reports/schedules/{schedule_id}/run?export_format=csv|json

## Performance

- GET /orgs/{org_id}/performance/activity-per-task?user_id=USER_ID&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&team_id=TEAM_ID&project_id=PROJECT_ID
