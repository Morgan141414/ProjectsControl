import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class AdminConsoleScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Admin console")
        title.setObjectName("TitleLabel")

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.tabs = QTabWidget()
        self.org_tab = QWidget()
        self.projects_tab = QWidget()
        self.teams_tab = QWidget()
        self.users_tab = QWidget()
        self.privacy_tab = QWidget()
        self.notifications_tab = QWidget()
        self.audit_tab = QWidget()
        self.schedules_tab = QWidget()

        self.tabs.addTab(self.org_tab, "Org")
        self.tabs.addTab(self.projects_tab, "Projects")
        self.tabs.addTab(self.teams_tab, "Teams")
        self.tabs.addTab(self.users_tab, "Users")
        self.tabs.addTab(self.privacy_tab, "Privacy")
        self.tabs.addTab(self.notifications_tab, "Notifications")
        self.tabs.addTab(self.audit_tab, "Audit")
        self.tabs.addTab(self.schedules_tab, "Schedules")

        self._build_org_tab()
        self._build_projects_tab()
        self._build_teams_tab()
        self._build_users_tab()
        self._build_privacy_tab()
        self._build_notifications_tab()
        self._build_audit_tab()
        self._build_schedules_tab()

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs)

    def _require_org(self) -> str | None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Join or create an organization first")
        return org_id

    def _build_org_tab(self) -> None:
        layout = QVBoxLayout(self.org_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        create_frame = QFrame()
        create_layout = QFormLayout(create_frame)
        create_layout.setContentsMargins(0, 0, 0, 0)

        self.org_name_input = QLineEdit()
        self.org_name_input.setPlaceholderText("Organization name")

        self.create_org_button = QPushButton("Create organization")
        self.create_org_button.clicked.connect(self.create_org)

        create_layout.addRow("Name", self.org_name_input)
        create_layout.addRow(self.create_org_button)

        self.join_requests_list = QListWidget()
        self.join_requests_list.itemSelectionChanged.connect(self._sync_join_request)

        self.refresh_requests_button = QPushButton("Refresh join requests")
        self.refresh_requests_button.clicked.connect(self.refresh_join_requests)

        request_controls = QHBoxLayout()
        self.approve_button = QPushButton("Approve")
        self.approve_button.clicked.connect(self.approve_request)
        self.reject_button = QPushButton("Reject")
        self.reject_button.clicked.connect(self.reject_request)

        request_controls.addWidget(self.approve_button)
        request_controls.addWidget(self.reject_button)
        request_controls.addStretch(1)

        layout.addWidget(create_frame)
        layout.addWidget(QLabel("Join requests"))
        layout.addWidget(self.join_requests_list)
        layout.addWidget(self.refresh_requests_button)
        layout.addLayout(request_controls)

    def _build_projects_tab(self) -> None:
        layout = QVBoxLayout(self.projects_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.projects_list = QListWidget()

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.project_name_input = QLineEdit()
        self.project_name_input.setPlaceholderText("Project name")

        self.project_description_input = QLineEdit()
        self.project_description_input.setPlaceholderText("Description")

        self.create_project_button = QPushButton("Create project")
        self.create_project_button.clicked.connect(self.create_project)

        self.refresh_projects_button = QPushButton("Refresh projects")
        self.refresh_projects_button.clicked.connect(self.refresh_projects)

        form_layout.addRow("Name", self.project_name_input)
        form_layout.addRow("Description", self.project_description_input)
        form_layout.addRow(self.create_project_button)

        layout.addWidget(self.projects_list)
        layout.addWidget(form)
        layout.addWidget(self.refresh_projects_button)

    def _build_teams_tab(self) -> None:
        layout = QVBoxLayout(self.teams_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.teams_list = QListWidget()
        self.teams_list.itemSelectionChanged.connect(self._sync_selected_team)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.team_name_input = QLineEdit()
        self.team_name_input.setPlaceholderText("Team name")

        self.team_project_input = QLineEdit()
        self.team_project_input.setPlaceholderText("Project id")

        self.team_member_input = QLineEdit()
        self.team_member_input.setPlaceholderText("User id to add")

        self.create_team_button = QPushButton("Create team")
        self.create_team_button.clicked.connect(self.create_team)

        self.add_member_button = QPushButton("Add member")
        self.add_member_button.clicked.connect(self.add_team_member)

        self.refresh_teams_button = QPushButton("Refresh teams")
        self.refresh_teams_button.clicked.connect(self.refresh_teams)

        form_layout.addRow("Name", self.team_name_input)
        form_layout.addRow("Project id", self.team_project_input)
        form_layout.addRow(self.create_team_button)
        form_layout.addRow("Member id", self.team_member_input)
        form_layout.addRow(self.add_member_button)

        layout.addWidget(self.teams_list)
        layout.addWidget(form)
        layout.addWidget(self.refresh_teams_button)

    def _build_users_tab(self) -> None:
        layout = QVBoxLayout(self.users_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.users_list = QListWidget()

        self.refresh_users_button = QPushButton("Refresh users")
        self.refresh_users_button.clicked.connect(self.refresh_users)

        layout.addWidget(self.users_list)
        layout.addWidget(self.refresh_users_button)

    def _build_privacy_tab(self) -> None:
        layout = QVBoxLayout(self.privacy_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.privacy_list = QListWidget()
        self.privacy_list.itemSelectionChanged.connect(self._sync_privacy_rule)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.privacy_target_input = QLineEdit()
        self.privacy_target_input.setPlaceholderText("app|url|window")

        self.privacy_match_input = QLineEdit()
        self.privacy_match_input.setPlaceholderText("contains|equals|regex")

        self.privacy_pattern_input = QLineEdit()
        self.privacy_pattern_input.setPlaceholderText("Pattern")

        self.privacy_action_input = QLineEdit()
        self.privacy_action_input.setPlaceholderText("mask|block|allow")

        self.create_privacy_button = QPushButton("Create rule")
        self.create_privacy_button.clicked.connect(self.create_privacy_rule)

        self.delete_privacy_button = QPushButton("Delete selected")
        self.delete_privacy_button.clicked.connect(self.delete_privacy_rule)

        form_layout.addRow("Target", self.privacy_target_input)
        form_layout.addRow("Match", self.privacy_match_input)
        form_layout.addRow("Pattern", self.privacy_pattern_input)
        form_layout.addRow("Action", self.privacy_action_input)
        form_layout.addRow(self.create_privacy_button)
        form_layout.addRow(self.delete_privacy_button)

        self.refresh_privacy_button = QPushButton("Refresh rules")
        self.refresh_privacy_button.clicked.connect(self.refresh_privacy_rules)

        layout.addWidget(self.privacy_list)
        layout.addWidget(form)
        layout.addWidget(self.refresh_privacy_button)

    def _build_notifications_tab(self) -> None:
        layout = QVBoxLayout(self.notifications_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.notifications_list = QListWidget()
        self.notifications_list.itemSelectionChanged.connect(self._sync_notification)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.notification_event_input = QLineEdit()
        self.notification_event_input.setPlaceholderText("event type")

        self.notification_url_input = QLineEdit()
        self.notification_url_input.setPlaceholderText("https://...")

        self.create_notification_button = QPushButton("Create hook")
        self.create_notification_button.clicked.connect(self.create_notification)

        self.delete_notification_button = QPushButton("Delete selected")
        self.delete_notification_button.clicked.connect(self.delete_notification)

        form_layout.addRow("Event type", self.notification_event_input)
        form_layout.addRow("URL", self.notification_url_input)
        form_layout.addRow(self.create_notification_button)
        form_layout.addRow(self.delete_notification_button)

        self.refresh_notifications_button = QPushButton("Refresh hooks")
        self.refresh_notifications_button.clicked.connect(self.refresh_notifications)

        layout.addWidget(self.notifications_list)
        layout.addWidget(form)
        layout.addWidget(self.refresh_notifications_button)

    def _build_audit_tab(self) -> None:
        layout = QVBoxLayout(self.audit_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.audit_list = QListWidget()

        self.refresh_audit_button = QPushButton("Refresh audit")
        self.refresh_audit_button.clicked.connect(self.refresh_audit)

        layout.addWidget(self.audit_list)
        layout.addWidget(self.refresh_audit_button)

    def _build_schedules_tab(self) -> None:
        layout = QVBoxLayout(self.schedules_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.schedules_list = QListWidget()

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.schedule_type_input = QLineEdit()
        self.schedule_type_input.setPlaceholderText("org-kpi or project-kpi")

        self.schedule_interval_input = QSpinBox()
        self.schedule_interval_input.setRange(1, 365)
        self.schedule_interval_input.setValue(7)

        self.schedule_start_input = QLineEdit()
        self.schedule_start_input.setPlaceholderText("YYYY-MM-DD")

        self.schedule_end_input = QLineEdit()
        self.schedule_end_input.setPlaceholderText("YYYY-MM-DD")

        self.schedule_team_input = QLineEdit()
        self.schedule_team_input.setPlaceholderText("Team id")

        self.schedule_project_input = QLineEdit()
        self.schedule_project_input.setPlaceholderText("Project id")

        self.schedule_format_input = QLineEdit("csv")
        self.schedule_format_input.setPlaceholderText("csv or json")

        self.create_schedule_button = QPushButton("Create schedule")
        self.create_schedule_button.clicked.connect(self.create_schedule)

        self.run_schedule_button = QPushButton("Run selected")
        self.run_schedule_button.clicked.connect(self.run_schedule)

        form_layout.addRow("Report type", self.schedule_type_input)
        form_layout.addRow("Interval days", self.schedule_interval_input)
        form_layout.addRow("Start date", self.schedule_start_input)
        form_layout.addRow("End date", self.schedule_end_input)
        form_layout.addRow("Team id", self.schedule_team_input)
        form_layout.addRow("Project id", self.schedule_project_input)
        form_layout.addRow("Export format", self.schedule_format_input)
        form_layout.addRow(self.create_schedule_button)
        form_layout.addRow(self.run_schedule_button)

        self.refresh_schedules_button = QPushButton("Refresh schedules")
        self.refresh_schedules_button.clicked.connect(self.refresh_schedules)

        layout.addWidget(self.schedules_list)
        layout.addWidget(form)
        layout.addWidget(self.refresh_schedules_button)

    def create_org(self) -> None:
        name = self.org_name_input.text().strip()
        if not name:
            self.status_label.setText("Organization name required")
            return

        self.create_org_button.setEnabled(False)
        try:
            response = api_client.create_org(name)
            org_id = response.get("id")
            if org_id:
                session_store.set_org_id(org_id)
            self.status_label.setText("Organization created")
            self.org_name_input.clear()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_org_button.setEnabled(True)

    def refresh_join_requests(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_requests_button.setEnabled(False)
        self.join_requests_list.clear()
        try:
            requests = api_client.list_join_requests(org_id)
            for request in requests:
                item = QListWidgetItem(self._pretty_json(request))
                item.setData(Qt.UserRole, request.get("id"))
                self.join_requests_list.addItem(item)
            if not requests:
                self.status_label.setText("No join requests")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_requests_button.setEnabled(True)

    def approve_request(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        request_id = self._selected_join_request()
        if not request_id:
            self.status_label.setText("Select a request")
            return

        self.approve_button.setEnabled(False)
        try:
            api_client.approve_join_request(org_id, request_id)
            self.status_label.setText("Request approved")
            self.refresh_join_requests()
        except ApiError as exc:
            self.status_label.setText(f"Approve failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Approve failed: {exc}")
        finally:
            self.approve_button.setEnabled(True)

    def reject_request(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        request_id = self._selected_join_request()
        if not request_id:
            self.status_label.setText("Select a request")
            return

        self.reject_button.setEnabled(False)
        try:
            api_client.reject_join_request(org_id, request_id)
            self.status_label.setText("Request rejected")
            self.refresh_join_requests()
        except ApiError as exc:
            self.status_label.setText(f"Reject failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Reject failed: {exc}")
        finally:
            self.reject_button.setEnabled(True)

    def refresh_projects(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_projects_button.setEnabled(False)
        self.projects_list.clear()
        try:
            projects = api_client.list_projects(org_id)
            for project in projects:
                item = QListWidgetItem(self._pretty_json(project))
                self.projects_list.addItem(item)
            if not projects:
                self.status_label.setText("No projects")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_projects_button.setEnabled(True)

    def create_project(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        name = self.project_name_input.text().strip()
        description = self.project_description_input.text().strip() or None
        if not name:
            self.status_label.setText("Project name required")
            return

        self.create_project_button.setEnabled(False)
        try:
            api_client.create_project(org_id, name=name, description=description)
            self.status_label.setText("Project created")
            self.project_name_input.clear()
            self.project_description_input.clear()
            self.refresh_projects()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_project_button.setEnabled(True)

    def refresh_teams(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_teams_button.setEnabled(False)
        self.teams_list.clear()
        try:
            teams = api_client.list_teams(org_id)
            for team in teams:
                item = QListWidgetItem(self._pretty_json(team))
                item.setData(Qt.UserRole, team.get("id"))
                self.teams_list.addItem(item)
            if not teams:
                self.status_label.setText("No teams")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_teams_button.setEnabled(True)

    def create_team(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        name = self.team_name_input.text().strip()
        project_id = self.team_project_input.text().strip() or None
        if not name:
            self.status_label.setText("Team name required")
            return

        self.create_team_button.setEnabled(False)
        try:
            api_client.create_team(org_id, name=name, project_id=project_id)
            self.status_label.setText("Team created")
            self.team_name_input.clear()
            self.team_project_input.clear()
            self.refresh_teams()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_team_button.setEnabled(True)

    def add_team_member(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        team_id = self._selected_team_id()
        if not team_id:
            self.status_label.setText("Select a team")
            return

        user_id = self.team_member_input.text().strip()
        if not user_id:
            self.status_label.setText("User id required")
            return

        self.add_member_button.setEnabled(False)
        try:
            api_client.add_team_member(org_id, team_id, user_id)
            self.status_label.setText("Member added")
            self.team_member_input.clear()
        except ApiError as exc:
            self.status_label.setText(f"Add failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Add failed: {exc}")
        finally:
            self.add_member_button.setEnabled(True)

    def refresh_users(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_users_button.setEnabled(False)
        self.users_list.clear()
        try:
            users = api_client.list_users(org_id)
            for user in users:
                item = QListWidgetItem(self._pretty_json(user))
                self.users_list.addItem(item)
            if not users:
                self.status_label.setText("No users")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_users_button.setEnabled(True)

    def refresh_privacy_rules(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_privacy_button.setEnabled(False)
        self.privacy_list.clear()
        try:
            rules = api_client.list_privacy_rules(org_id)
            for rule in rules:
                item = QListWidgetItem(self._pretty_json(rule))
                item.setData(Qt.UserRole, rule.get("id"))
                self.privacy_list.addItem(item)
            if not rules:
                self.status_label.setText("No privacy rules")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_privacy_button.setEnabled(True)

    def create_privacy_rule(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        target = self.privacy_target_input.text().strip()
        match_type = self.privacy_match_input.text().strip()
        pattern = self.privacy_pattern_input.text().strip()
        action = self.privacy_action_input.text().strip()
        if not target or not match_type or not pattern or not action:
            self.status_label.setText("All privacy fields required")
            return

        self.create_privacy_button.setEnabled(False)
        try:
            api_client.create_privacy_rule(
                org_id,
                target=target,
                match_type=match_type,
                pattern=pattern,
                action=action,
            )
            self.status_label.setText("Privacy rule created")
            self.privacy_target_input.clear()
            self.privacy_match_input.clear()
            self.privacy_pattern_input.clear()
            self.privacy_action_input.clear()
            self.refresh_privacy_rules()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_privacy_button.setEnabled(True)

    def delete_privacy_rule(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        rule_id = self._selected_privacy_rule()
        if not rule_id:
            self.status_label.setText("Select a privacy rule")
            return

        self.delete_privacy_button.setEnabled(False)
        try:
            api_client.delete_privacy_rule(org_id, rule_id)
            self.status_label.setText("Privacy rule deleted")
            self.refresh_privacy_rules()
        except ApiError as exc:
            self.status_label.setText(f"Delete failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Delete failed: {exc}")
        finally:
            self.delete_privacy_button.setEnabled(True)

    def refresh_notifications(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_notifications_button.setEnabled(False)
        self.notifications_list.clear()
        try:
            hooks = api_client.list_notification_hooks(org_id)
            for hook in hooks:
                item = QListWidgetItem(self._pretty_json(hook))
                item.setData(Qt.UserRole, hook.get("id"))
                self.notifications_list.addItem(item)
            if not hooks:
                self.status_label.setText("No notification hooks")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_notifications_button.setEnabled(True)

    def create_notification(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        event_type = self.notification_event_input.text().strip()
        url = self.notification_url_input.text().strip()
        if not event_type or not url:
            self.status_label.setText("Event type and URL required")
            return

        self.create_notification_button.setEnabled(False)
        try:
            api_client.create_notification_hook(org_id, event_type=event_type, url=url)
            self.status_label.setText("Notification hook created")
            self.notification_event_input.clear()
            self.notification_url_input.clear()
            self.refresh_notifications()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_notification_button.setEnabled(True)

    def delete_notification(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        hook_id = self._selected_notification()
        if not hook_id:
            self.status_label.setText("Select a hook")
            return

        self.delete_notification_button.setEnabled(False)
        try:
            api_client.delete_notification_hook(org_id, hook_id)
            self.status_label.setText("Notification hook deleted")
            self.refresh_notifications()
        except ApiError as exc:
            self.status_label.setText(f"Delete failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Delete failed: {exc}")
        finally:
            self.delete_notification_button.setEnabled(True)

    def refresh_audit(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_audit_button.setEnabled(False)
        self.audit_list.clear()
        try:
            events = api_client.list_audit(org_id)
            for event in events:
                item = QListWidgetItem(self._pretty_json(event))
                self.audit_list.addItem(item)
            if not events:
                self.status_label.setText("No audit events")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_audit_button.setEnabled(True)

    def refresh_schedules(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_schedules_button.setEnabled(False)
        self.schedules_list.clear()
        try:
            schedules = api_client.list_report_schedules(org_id)
            for schedule in schedules:
                item = QListWidgetItem(self._pretty_json(schedule))
                item.setData(Qt.UserRole, schedule.get("id"))
                self.schedules_list.addItem(item)
            if not schedules:
                self.status_label.setText("No schedules")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_schedules_button.setEnabled(True)

    def create_schedule(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        report_type = self.schedule_type_input.text().strip()
        if not report_type:
            self.status_label.setText("Report type required")
            return

        interval_days = self.schedule_interval_input.value()
        start_date = self.schedule_start_input.text().strip() or None
        end_date = self.schedule_end_input.text().strip() or None
        team_id = self.schedule_team_input.text().strip() or None
        project_id = self.schedule_project_input.text().strip() or None

        self.create_schedule_button.setEnabled(False)
        try:
            api_client.create_report_schedule(
                org_id,
                report_type=report_type,
                interval_days=interval_days,
                start_date=start_date,
                end_date=end_date,
                team_id=team_id,
                project_id=project_id,
            )
            self.status_label.setText("Schedule created")
            self.schedule_type_input.clear()
            self.schedule_start_input.clear()
            self.schedule_end_input.clear()
            self.schedule_team_input.clear()
            self.schedule_project_input.clear()
            self.refresh_schedules()
        except ApiError as exc:
            self.status_label.setText(f"Create failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Create failed: {exc}")
        finally:
            self.create_schedule_button.setEnabled(True)

    def run_schedule(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        schedule_id = self._selected_schedule_id()
        if not schedule_id:
            self.status_label.setText("Select a schedule")
            return

        export_format = self.schedule_format_input.text().strip() or "csv"

        self.run_schedule_button.setEnabled(False)
        try:
            api_client.run_report_schedule(org_id, schedule_id, export_format)
            self.status_label.setText("Schedule triggered")
        except ApiError as exc:
            self.status_label.setText(f"Run failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Run failed: {exc}")
        finally:
            self.run_schedule_button.setEnabled(True)

    def _sync_join_request(self) -> None:
        pass

    def _sync_selected_team(self) -> None:
        selected = self.teams_list.selectedItems()
        if not selected:
            return
        team_id = selected[0].data(Qt.UserRole)
        if team_id:
            self.team_project_input.setText("")

    def _sync_privacy_rule(self) -> None:
        pass

    def _sync_notification(self) -> None:
        pass

    def _selected_join_request(self) -> str | None:
        selected = self.join_requests_list.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.UserRole)

    def _selected_team_id(self) -> str | None:
        selected = self.teams_list.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.UserRole)

    def _selected_privacy_rule(self) -> str | None:
        selected = self.privacy_list.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.UserRole)

    def _selected_notification(self) -> str | None:
        selected = self.notifications_list.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.UserRole)

    def _selected_schedule_id(self) -> str | None:
        selected = self.schedules_list.selectedItems()
        if not selected:
            return None
        return selected[0].data(Qt.UserRole)

    def _pretty_json(self, payload: object) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=True)
