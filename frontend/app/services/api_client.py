import httpx

from app.state.session import session_store


class ApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if session_store.token:
            return {"Authorization": f"Bearer {session_store.token}"}
        return {}

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = httpx.request(method, f"{self.base_url}{path}", timeout=10, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as exc:
            detail = "Unexpected error"
            try:
                detail = exc.response.json().get("detail", detail)
            except Exception:  # noqa: BLE001
                detail = exc.response.text or detail
            raise ApiError(detail, exc.response.status_code) from exc
        except httpx.RequestError as exc:
            raise ApiError("Network error. Check backend status.") from exc

    def register(self, email: str, password: str, full_name: str) -> dict:
        response = self._request(
            "POST",
            "/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        return response.json()

    def login(self, email: str, password: str) -> str:
        response = self._request(
            "POST",
            "/auth/login",
            data={"username": email, "password": password},
        )
        return response.json()["access_token"]

    def google_login(self, id_token: str) -> str:
        response = self._request(
            "POST",
            "/auth/google",
            json={"id_token": id_token},
        )
        return response.json()["access_token"]

    def join_org(self, org_code: str) -> dict:
        response = self._request(
            "POST",
            "/orgs/join-request",
            json={"org_code": org_code},
            headers=self._headers(),
        )
        return response.json()

    def get_org(self, org_id: str) -> dict:
        response = self._request(
            "GET",
            f"/orgs/{org_id}",
            headers=self._headers(),
        )
        return response.json()

    def create_org(self, name: str) -> dict:
        response = self._request(
            "POST",
            "/orgs",
            json={"name": name},
            headers=self._headers(),
        )
        return response.json()

    def list_join_requests(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/join-requests",
            headers=self._headers(),
        )
        return response.json()

    def approve_join_request(self, org_id: str, request_id: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/join-requests/{request_id}/approve",
            headers=self._headers(),
        )
        return response.json()

    def reject_join_request(self, org_id: str, request_id: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/join-requests/{request_id}/reject",
            headers=self._headers(),
        )
        return response.json()

    def list_today_tasks(self, org_id: str, project_id: str | None = None) -> list[dict]:
        params = {"project_id": project_id} if project_id else None
        response = self._request(
            "GET",
            f"/orgs/{org_id}/tasks/today",
            params=params,
            headers=self._headers(),
        )
        return response.json()

    def create_task(
        self,
        org_id: str,
        title: str,
        description: str | None,
        due_date: str | None,
        assignee_id: str | None,
        team_id: str | None,
    ) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/tasks",
            json={
                "title": title,
                "description": description,
                "due_date": due_date,
                "assignee_id": assignee_id,
                "team_id": team_id,
            },
            headers=self._headers(),
        )
        return response.json()

    def update_task(self, org_id: str, task_id: str, status: str | None, report: str | None) -> dict:
        response = self._request(
            "PATCH",
            f"/orgs/{org_id}/tasks/{task_id}",
            json={"status": status, "report": report},
            headers=self._headers(),
        )
        return response.json()

    def start_session(self, org_id: str, device_name: str, os_name: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/sessions/start",
            json={"device_name": device_name, "os_name": os_name},
            headers=self._headers(),
        )
        return response.json()

    def stop_session(self, org_id: str, session_id: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/sessions/{session_id}/stop",
            json={},
            headers=self._headers(),
        )
        return response.json()

    def list_my_sessions(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/sessions/me",
            headers=self._headers(),
        )
        return response.json()

    def list_org_sessions(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/sessions",
            headers=self._headers(),
        )
        return response.json()

    def upload_recording(self, org_id: str, session_id: str, file_path: str) -> dict:
        with open(file_path, "rb") as handle:
            response = self._request(
                "POST",
                f"/orgs/{org_id}/sessions/{session_id}/recordings",
                files={"file": handle},
                headers=self._headers(),
            )
        return response.json()

    def list_recordings(self, org_id: str, session_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/sessions/{session_id}/recordings",
            headers=self._headers(),
        )
        return response.json()

    def get_org_kpi(
        self,
        org_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if team_id:
            params["team_id"] = team_id
        if project_id:
            params["project_id"] = project_id
        response = self._request(
            "GET",
            f"/orgs/{org_id}/reports/kpi",
            params=params or None,
            headers=self._headers(),
        )
        return response.json()

    def get_project_kpi(
        self,
        org_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        response = self._request(
            "GET",
            f"/orgs/{org_id}/reports/projects/kpi",
            params=params or None,
            headers=self._headers(),
        )
        return response.json()

    def export_org_kpi(
        self,
        org_id: str,
        export_format: str = "csv",
        start_date: str | None = None,
        end_date: str | None = None,
        team_id: str | None = None,
        project_id: str | None = None,
    ) -> dict:
        params: dict[str, str] = {"export_format": export_format}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if team_id:
            params["team_id"] = team_id
        if project_id:
            params["project_id"] = project_id
        response = self._request(
            "POST",
            f"/orgs/{org_id}/reports/exports/org-kpi",
            params=params,
            headers=self._headers(),
        )
        return response.json()

    def export_project_kpi(
        self,
        org_id: str,
        export_format: str = "csv",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        params: dict[str, str] = {"export_format": export_format}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        response = self._request(
            "POST",
            f"/orgs/{org_id}/reports/exports/project-kpi",
            params=params,
            headers=self._headers(),
        )
        return response.json()

    def list_projects(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/projects",
            headers=self._headers(),
        )
        return response.json()

    def create_project(self, org_id: str, name: str, description: str | None) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/projects",
            json={"name": name, "description": description},
            headers=self._headers(),
        )
        return response.json()

    def list_teams(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/teams",
            headers=self._headers(),
        )
        return response.json()

    def list_my_teams(self, org_id: str, project_id: str | None = None) -> list[dict]:
        params = {"project_id": project_id} if project_id else None
        response = self._request(
            "GET",
            f"/orgs/{org_id}/teams/me",
            params=params,
            headers=self._headers(),
        )
        return response.json()

    def create_team(self, org_id: str, name: str, project_id: str | None) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/teams",
            json={"name": name, "project_id": project_id},
            headers=self._headers(),
        )
        return response.json()

    def update_team(self, org_id: str, team_id: str, name: str | None, project_id: str | None) -> dict:
        response = self._request(
            "PATCH",
            f"/orgs/{org_id}/teams/{team_id}",
            json={"name": name, "project_id": project_id},
            headers=self._headers(),
        )
        return response.json()

    def add_team_member(self, org_id: str, team_id: str, user_id: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/teams/{team_id}/members",
            json={"user_id": user_id},
            headers=self._headers(),
        )
        return response.json()

    def list_users(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/users",
            headers=self._headers(),
        )
        return response.json()

    def list_privacy_rules(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/privacy/rules",
            headers=self._headers(),
        )
        return response.json()

    def create_privacy_rule(
        self,
        org_id: str,
        target: str,
        match_type: str,
        pattern: str,
        action: str,
    ) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/privacy/rules",
            json={
                "target": target,
                "match_type": match_type,
                "pattern": pattern,
                "action": action,
                "enabled": True,
            },
            headers=self._headers(),
        )
        return response.json()

    def update_privacy_rule(
        self,
        org_id: str,
        rule_id: str,
        pattern: str | None,
        action: str | None,
        enabled: bool | None,
    ) -> dict:
        response = self._request(
            "PATCH",
            f"/orgs/{org_id}/privacy/rules/{rule_id}",
            json={"pattern": pattern, "action": action, "enabled": enabled},
            headers=self._headers(),
        )
        return response.json()

    def delete_privacy_rule(self, org_id: str, rule_id: str) -> dict:
        response = self._request(
            "DELETE",
            f"/orgs/{org_id}/privacy/rules/{rule_id}",
            headers=self._headers(),
        )
        return response.json()

    def list_notification_hooks(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/notifications",
            headers=self._headers(),
        )
        return response.json()

    def create_notification_hook(self, org_id: str, event_type: str, url: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/notifications",
            json={"event_type": event_type, "url": url, "enabled": True},
            headers=self._headers(),
        )
        return response.json()

    def update_notification_hook(
        self,
        org_id: str,
        hook_id: str,
        url: str | None,
        enabled: bool | None,
    ) -> dict:
        response = self._request(
            "PATCH",
            f"/orgs/{org_id}/notifications/{hook_id}",
            json={"url": url, "enabled": enabled},
            headers=self._headers(),
        )
        return response.json()

    def delete_notification_hook(self, org_id: str, hook_id: str) -> dict:
        response = self._request(
            "DELETE",
            f"/orgs/{org_id}/notifications/{hook_id}",
            headers=self._headers(),
        )
        return response.json()

    def list_audit(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/audit",
            headers=self._headers(),
        )
        return response.json()

    def get_session_metrics(self, org_id: str, session_id: str) -> dict:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/metrics/sessions/{session_id}",
            headers=self._headers(),
        )
        return response.json()

    def get_user_metrics(
        self,
        org_id: str,
        user_id: str,
        start_date: str | None,
        end_date: str | None,
        project_id: str | None,
    ) -> dict:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if project_id:
            params["project_id"] = project_id
        response = self._request(
            "GET",
            f"/orgs/{org_id}/metrics/users/{user_id}",
            params=params or None,
            headers=self._headers(),
        )
        return response.json()

    def get_activity_per_task(
        self,
        org_id: str,
        user_id: str | None,
        start_date: str | None,
        end_date: str | None,
        team_id: str | None,
        project_id: str | None,
    ) -> dict:
        params: dict[str, str] = {}
        if user_id:
            params["user_id"] = user_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if team_id:
            params["team_id"] = team_id
        if project_id:
            params["project_id"] = project_id
        response = self._request(
            "GET",
            f"/orgs/{org_id}/performance/activity-per-task",
            params=params or None,
            headers=self._headers(),
        )
        return response.json()

    def list_report_exports(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/reports/exports",
            headers=self._headers(),
        )
        return response.json()

    def get_ai_kpi(
        self,
        org_id: str,
        start_date: str | None,
        end_date: str | None,
        team_id: str | None,
        project_id: str | None,
    ) -> dict:
        params: dict[str, str] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if team_id:
            params["team_id"] = team_id
        if project_id:
            params["project_id"] = project_id
        response = self._request(
            "GET",
            f"/orgs/{org_id}/ai/kpi",
            params=params or None,
            headers=self._headers(),
        )
        return response.json()

    def get_ai_scorecards(
        self,
        org_id: str,
        period: str,
        as_of: str | None,
        user_id: str | None,
        mode: str | None,
        role_profile: str | None,
        trend_limit: int | None,
    ) -> list[dict]:
        params: dict[str, str] = {"period": period}
        if as_of:
            params["as_of"] = as_of
        if user_id:
            params["user_id"] = user_id
        if mode:
            params["mode"] = mode
        if role_profile:
            params["role_profile"] = role_profile
        if trend_limit:
            params["trend_limit"] = str(trend_limit)
        response = self._request(
            "GET",
            f"/orgs/{org_id}/ai/scorecards",
            params=params,
            headers=self._headers(),
        )
        return response.json()

    def get_consent_status(self, org_id: str) -> dict:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/consent/me",
            headers=self._headers(),
        )
        return response.json()

    def accept_consent(self, org_id: str, policy_version: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/consent/accept",
            json={"policy_version": policy_version},
            headers=self._headers(),
        )
        return response.json()

    def get_me(self) -> dict:
        response = self._request(
            "GET",
            "/users/me",
            headers=self._headers(),
        )
        return response.json()

    def update_me(self, payload: dict) -> dict:
        response = self._request(
            "PATCH",
            "/users/me",
            json=payload,
            headers=self._headers(),
        )
        return response.json()

    def create_daily_report(self, org_id: str, project_id: str, report_date: str | None, content: str) -> dict:
        payload: dict[str, str] = {"project_id": project_id, "content": content}
        if report_date:
            payload["report_date"] = report_date
        response = self._request(
            "POST",
            f"/orgs/{org_id}/daily-reports",
            json=payload,
            headers=self._headers(),
        )
        return response.json()

    def download_report_export(self, org_id: str, export_id: str) -> bytes:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/reports/exports/{export_id}/download",
            headers=self._headers(),
        )
        return response.content

    def create_report_schedule(
        self,
        org_id: str,
        report_type: str,
        interval_days: int,
        start_date: str | None,
        end_date: str | None,
        team_id: str | None,
        project_id: str | None,
    ) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/reports/schedules",
            json={
                "report_type": report_type,
                "interval_days": interval_days,
                "start_date": start_date,
                "end_date": end_date,
                "team_id": team_id,
                "project_id": project_id,
            },
            headers=self._headers(),
        )
        return response.json()

    def list_report_schedules(self, org_id: str) -> list[dict]:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/reports/schedules",
            headers=self._headers(),
        )
        return response.json()

    def run_report_schedule(self, org_id: str, schedule_id: str, export_format: str) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/reports/schedules/{schedule_id}/run",
            params={"export_format": export_format},
            headers=self._headers(),
        )
        return response.json()

    def download_recording(self, org_id: str, recording_id: str) -> bytes:
        response = self._request(
            "GET",
            f"/orgs/{org_id}/recordings/{recording_id}/download",
            headers=self._headers(),
        )
        return response.content

    def cleanup_recordings(self, org_id: str, days: int) -> dict:
        response = self._request(
            "POST",
            f"/orgs/{org_id}/recordings/cleanup",
            json={"days": days},
            headers=self._headers(),
        )
        return response.json()


api_client = ApiClient("http://127.0.0.1:8001")
